# user_routes.py

from fastapi import APIRouter, Depends, HTTPException
from pymongo.collection import Collection
from database import database
from models import User_login

router = APIRouter()

# @router.get("/user/{user_id}")
# async def get_user(user_id: str):
#     users_collection: Collection = database["users"]
#     user_data = users_collection.find_one({"_id": user_id})
#     if not user_data:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user_data
