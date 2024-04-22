# user_routes.py

from fastapi import APIRouter, Depends, HTTPException
from database import collection_add_vacancy,collection_user
from models import add_vacancy,User
from models import User_login
from utils import hash_password, verify_password,create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

router = APIRouter()


@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = collection_user.find_one({"user_email": form_data.username})
    if user and verify_password(form_data.password, user['user_pw']):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"email": user['user_email']}, expires_delta=access_token_expires)
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Incorrect email or password")


vacancy_counter = 1
@router.post("/create_vacancy")
def create_vacancy(request_data: add_vacancy, current_user: User = Depends(get_current_user)):
    global vacancy_counter
    vacancy_id = f"A{vacancy_counter:03d}"
    vacancy_counter += 1
    data = {
        "vacancy_id": vacancy_id,
        "user_type": current_user.get('user_type'),
        "user_email": current_user.get("user_email"),
        "project_type": request_data.project_type,
        "pre_requisits": request_data.pre_requisits,
        "possition": request_data.possition,
        "num_of_vacancies": request_data.num_of_vacancies,
        "responsibilities": request_data.responsibilities,
        "more_details": request_data.more_details
    }
    collection_add_vacancy.insert_one(data)
    return {"message": "Vacancy created successfully"}

@router.get("/get_vacancies")
def get_vacancies(current_user: User = Depends(get_current_user)):
    vacancies = []
    for vacancy in collection_add_vacancy.find({"user_email": current_user.get("user_email")}):
        vacancy_data = {
            "vacancy_id": vacancy["vacancy_id"],
            "project_type": vacancy["project_type"],
            "possition": vacancy["possition"],
            "num_of_vacancies": vacancy["num_of_vacancies"],
        }
        vacancies.append(vacancy_data)
    return vacancies

@router.get("/profile")
def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

