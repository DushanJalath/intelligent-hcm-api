# auth_routes.py
from fastapi import APIRouter, HTTPException
from database import collection_user_login
from models import User_login
from utils import hash_password, verify_password,create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta
from fastapi import Depends

router = APIRouter()

@router.post("/signup")
async def signup(user: User_login):
    existing_user = collection_user_login.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = hash_password(user.password)
    user_data = user.dict()
    user_data["password"] = hashed_password
    collection_user_login.insert_one(user_data)
    return {"message": "User registered successfully"}

@router.post("/login")
async def login(user: User_login):
    existing_user = collection_user_login.find_one({"email": user.email})
    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(user.password, existing_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {"access_token": access_token}

