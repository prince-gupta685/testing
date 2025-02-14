from datetime import timedelta, datetime
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
# from pymongo import MongoClient
from bson import ObjectId  # To handle ObjectId types
from motor.motor_asyncio import AsyncIOMotorClient
from argon2 import PasswordHasher
import jwt
import mailtrap as mt


app = FastAPI()

# Mongo_url ="mongodb+srv://gprince000685:testdb@cluster0test.d0mpr.mongodb.net/"
# client = MongoClient(Mongo_url)
# db = client.testdb
# collection = db.items
MONGO_DETAILS = "mongodb+srv://gprince000685:testdb@cluster0test.d0mpr.mongodb.net/"

client = AsyncIOMotorClient(MONGO_DETAILS)
db = client.testdb                                                                                                                                                                                                                                                                                 

# Create a PasswordHasher instance
ph = PasswordHasher()
OTP_EXPIRATION_TIME = 10  # OTP expiration time in minutes

otp_store = {}  # Store the OTPs in memory

SECRET_KEY = "headstart"
ALGORITHM = "HS256"

class RegUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

    def hash_password(self):
        return ph.hash(self.password)

# Pydantic model for the response that will hold the JWT token
class Token(BaseModel):
    access_token: str
    token_type: str 

# Helper function to convert ObjectId to string
def convert_objectid_to_str(user):
    user["_id"] = str(user["_id"])
    return user

# Helper function to verify password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except Exception:
        return False  # Return False if the verification fails

# Helper function to generate JWT token
def create_jwt_token(user_id: str) -> Token:
    access_token = jwt.encode({"user_id": user_id}, SECRET_KEY, algorithm=ALGORITHM)
    return Token(access_token=access_token, token_type="bearer")

def verify_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def generate_otp() -> str:
    return str(random.randint(100000, 999999))  # 6-digit OTP

# Function to send OTP email via SendGrid
def send_otp_email(to_email: EmailStr, otp: str):

    mail = mt.Mail(
        sender=mt.Address(email="hello@demomailtrap.com", name="Mailtrap Test"),
        to=[mt.Address(email=f"{to_email}", name="User")],
        subject="OTP to reset your password",
        text="Please use the following OTP to reset your password: {otp}",
        category="Integration Test",
    )

    client = mt.MailtrapClient(token="35360d67f980ffc58b893176e8b92811")
    response = client.send(mail)

# Function to store OTP with expiration time
def store_otp(email: EmailStr, otp: str):
    otp_store[email] = {
        "otp": otp,
        "expiration": datetime.now() + timedelta(minutes=OTP_EXPIRATION_TIME)
    }

# Function to verify OTP
def verify_otp(email: EmailStr, otp: str) -> bool:
    otp_data = otp_store.get(email)
    if otp_data:
        # Check if OTP is expired
        if datetime.utcnow() > otp_data["expiration"]:
            return False  # OTP has expired
        # Check if OTP matches
        return otp_data["otp"] == otp
    return False  # No OTP generated for the email


@app.get("/")  # Home route
def read_root():
    return {"message": "Welcome to the API"}

@app.post("/user/registration/")
async def user_registration(user: RegUser):
    existing_user = await db.RegUser.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user.password = user.hash_password()
    result = await db.RegUser.insert_one(user.dict())
    new_user = await db.RegUser.find_one({"_id": result.inserted_id})
    return convert_objectid_to_str(new_user)

@app.post("/user/login/", response_model=Token)  # Login route
async def user_login(email: str, password: str):
    user = await db.RegUser.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")  # Return 401 status code if the credentials are invalid
    access_token = create_jwt_token(str(user["_id"]))  # Create a JWT token
    return access_token

@app.post('/forgotpassword/')  # Forgot password route
async def forgot_password(email: str):
    user = await db.RegUser.find_one({"email": email})  # Check if the user exists
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Send an email with the otp to reset the password
    otp = generate_otp()
    print(otp)
    send_otp_email(email, otp)
    store_otp(email, otp)
    return {"message": "OTP sent to the email"}  # Return a success message

@app.post('/resetpassword/')  # Reset password route
async def reset_password(email: str, otp: str, new_password: str):
    if not verify_otp(email, otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")
    hashed_password = ph.hash(new_password) # Hash the new password
    result = await db.RegUser.update_one({"email": email}, {"$set": {"password": hashed_password}})
    if result.modified_count:
        return {"message": "Password reset successfully"}  # Return a success message  
    raise HTTPException(status_code=404, detail="User not found")


@app.get('/protected/')  # Protected route
async def protected_route(token: str):
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.RegUser.find_one({"_id": ObjectId(payload["user_id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return convert_objectid_to_str(user)