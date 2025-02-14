from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
# from pymongo import MongoClient
from bson import ObjectId  # To handle ObjectId types
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()

# Mongo_url ="mongodb+srv://gprince000685:testdb@cluster0test.d0mpr.mongodb.net/"
# client = MongoClient(Mongo_url)
# db = client.testdb
# collection = db.items
MONGO_DETAILS = "mongodb+srv://gprince000685:testdb@cluster0test.d0mpr.mongodb.net/"

client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.testdb
user_collection = database.User
user_detail_collection = database.UserDetails



class User(BaseModel):
    first_name: str
    last_name: str
    age: int

class UserDetails(BaseModel):
    user_id: str
    address: str
    phone: str

# Helper function to convert ObjectId to string
def convert_objectid_to_str(user):
    user["_id"] = str(user["_id"])
    return user

@app.get("/")  # Home route
def read_root():
    return {"message": "Welcome to the API"}

# Create a new user
@app.post("/adduser/")
async def create_user(user: User):
    result = await user_collection.insert_one(user.dict())
    new_user = await user_collection.find_one({"_id": result.inserted_id})
    return convert_objectid_to_str(new_user)

@app.post("/adduserdetail/")
async def create_user(user_detail: UserDetails):
    existing_user = await user_collection.find_one({"_id": ObjectId(user_detail.user_id)})
    print(existing_user)
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    detail = await user_detail_collection.insert_one(user_detail.dict())
    user_details = await user_detail_collection.find_one({"_id": ObjectId(detail.inserted_id)})
    
    return convert_objectid_to_str(user_details)


# get all users
@app.get("/users/")
async def get_users():
    users = await user_collection.find().to_list(1000)
    return [convert_objectid_to_str(user) for user in users]

# get an user by ID
@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await user_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        return convert_objectid_to_str(user)
    raise HTTPException(status_code=404, detail="User not found")

# Update an user details
@app.put("/users/{user_id}")
async def update_user(user_id: str, user: User):
    result = await user_collection.update_one({"_id": ObjectId(user_id)}, {"$set": user.dict()})
    if result.matched_count:
        updated_user = await user_collection.find_one({"_id": ObjectId(user_id)})
        return convert_objectid_to_str(updated_user)
    raise HTTPException(status_code=404, detail="User not found")

# Delete an user
@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    result = await user_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count:
        return {"message": "User deleted successfully"}
    raise HTTPException(status_code=404, detail="User not found")
