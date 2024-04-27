# user_routes.py

from fastapi import APIRouter, Depends, HTTPException
from database import collection_add_vacancy,collection_user
from models import add_vacancy,User
from models import User_login,UpdateVacancyStatus
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

@router.post("/create_vacancy")
def create_vacancy(request_data: add_vacancy, current_user: User = Depends(get_current_user)):
    # Use findAndModify to atomically increment the vacancy_counter
    counter = collection_add_vacancy.find_one_and_update(
        {"_id": "vacancy_counter"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    vacancy_id = f"A{counter['seq']:03d}"

    data = {
        "vacancy_id": vacancy_id,
        "user_type": current_user.get('user_type'),
        "user_email": current_user.get("user_email"),
        "project_type": request_data.project_type,
        "pre_requisits": request_data.pre_requisits,
        "possition": request_data.possition,
        "num_of_vacancies": request_data.num_of_vacancies,
        "responsibilities": request_data.responsibilities,
        "more_details": request_data.more_details,
        "status": "pending"
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
            "status": vacancy["num_of_vacancies"]
        }
        vacancies.append(vacancy_data)
    return vacancies

@router.get("/profile")
def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/approve_vacancy/{vacancy_id}")
def approve_vacancy(vacancy_id: str, current_user: User = Depends(get_current_user)):
    # Check if the current user is an HR user
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can approve vacancies")

    # Update the vacancy status in the database
    updated = collection_add_vacancy.update_one(
        {"vacancy_id": vacancy_id},
        {"$set": {"status": "approved"}}
    )
    if updated.modified_count > 0:
        return {"message": "Vacancy approved successfully"}
    else:
        raise HTTPException(status_code=404, detail="Vacancy not found")

@router.post("/reject_vacancy/{vacancy_id}")
def reject_vacancy(vacancy_id: str, current_user: User = Depends(get_current_user)):
    # Check if the current user is an HR user
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can reject vacancies")

    # Update the vacancy status in the database
    updated = collection_add_vacancy.update_one(
        {"vacancy_id": vacancy_id},
        {"$set": {"status": "rejected"}}
    )
    if updated.modified_count > 0:
        return {"message": "Vacancy rejected successfully"}
    else:
        raise HTTPException(status_code=404, detail="Vacancy not found")

@router.get("/get_hr_vacancies")
def get_hr_vacancies(current_user: User = Depends(get_current_user)):
    # Check if the current user is an HR user
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view vacancies")

    # Define the statuses to exclude
    excluded_statuses = ["approved", "rejected"]

    vacancies = []
    for vacancy in collection_add_vacancy.find({"status": {"$nin": excluded_statuses}}):
        vacancy_data = {
            "vacancy_id": vacancy["vacancy_id"],
            "project_type": vacancy["project_type"],
            "possition": vacancy["possition"],
            "num_of_vacancies": vacancy["num_of_vacancies"]
        }
        vacancies.append(vacancy_data)
    return vacancies


@router.put("/update_hr_vacancy/{vacancy_id}")
def update_hr_vacancy(vacancy_id: str, status_data: UpdateVacancyStatus, current_user: User = Depends(get_current_user)):
    # Check if the current user is an HR user
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can update vacancies")

    # Check if the vacancy exists
    existing_vacancy = collection_add_vacancy.find_one({"vacancy_id": vacancy_id})
    if not existing_vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    # Update the status of the vacancy
    collection_add_vacancy.update_one({"vacancy_id": vacancy_id}, {"$set": {"status": status_data.new_status}})

    return {"message": f"Vacancy {vacancy_id} updated successfully"}
