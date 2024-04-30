# user_routes.py

from fastapi import APIRouter, Depends, HTTPException
from database import collection_add_vacancy,collection_user,collection_bills,collection_new_candidate
from models import add_vacancy,User ,UpdateVacancyStatus,Bills,Candidate,UpdateCandidateStatus
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
    last_vacancy = collection_add_vacancy.find_one(sort=[("_id", -1)])
    last_id = last_vacancy["vacancy_id"] if last_vacancy else "A000"

    last_seq = int(last_id[1:])  
    new_seq = last_seq + 1

    # Format the new vacancy ID
    vacancy_id = f"A{new_seq:03d}"

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
        "status": "pending",
        "publish_status":"pending",
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
            "status": vacancy["status"],
            "publish_status": vacancy["publish_status"]
        }
        vacancies.append(vacancy_data)
    return vacancies

@router.get("/profile")
def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

# @router.post("/approve_vacancy/{vacancy_id}")
# def approve_vacancy(vacancy_id: str, current_user: User = Depends(get_current_user)):
#     # Check if the current user is an HR user
#     if current_user.get('user_type') != "HR":
#         raise HTTPException(status_code=403, detail="Unauthorized, only HR can approve vacancies")

#     # Update the vacancy status in the database
#     updated = collection_add_vacancy.update_one(
#         {"vacancy_id": vacancy_id},
#         {"$set": {"status": "approved"}}
#     )
#     if updated.modified_count > 0:
#         return {"message": "Vacancy approved successfully"}
#     else:
#         raise HTTPException(status_code=404, detail="Vacancy not found")

# @router.post("/reject_vacancy/{vacancy_id}")
# def reject_vacancy(vacancy_id: str, current_user: User = Depends(get_current_user)):
#     # Check if the current user is an HR user
#     if current_user.get('user_type') != "HR":
#         raise HTTPException(status_code=403, detail="Unauthorized, only HR can reject vacancies")

#     # Update the vacancy status in the database
#     updated = collection_add_vacancy.update_one(
#         {"vacancy_id": vacancy_id},
#         {"$set": {"status": "rejected"}}
#     )
#     if updated.modified_count > 0:
#         return {"message": "Vacancy rejected successfully"}
#     else:
#         raise HTTPException(status_code=404, detail="Vacancy not found")

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


@router.post("/create_bill")
def create_bill(request_data: Bills ,current_user: User = Depends(get_current_user)):
    last_bill = collection_bills.find_one(sort=[("_id", -1)])
    last_id = last_bill["bill_id"] if last_bill else "B000"

    last_seq = int(last_id[1:])  
    new_seq = last_seq + 1

    # Format the new bill ID
    bill_id = f"B{new_seq:03d}"

    data = {
        "bill_id": bill_id,
        "user_type": current_user.get('user_type'),
        "user_email": current_user.get("user_email"),
        "amount": request_data.amount,
        "category": request_data.category,
        "u_id": request_data.u_id,
        "storename": request_data.storename,
        "Date": request_data.Date,
        "status": "pending"
    }
    collection_bills.insert_one(data)
    return {"message": "Bill created successfully"}

@router.get("/get_hr_bills")
def get_hr_bills(current_user: User = Depends(get_current_user)):
    # Check if the current user is an HR user
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view vacancies")

    # Define the statuses to exclude
    excluded_statuses = ["approved", "rejected"]

    bills_hr = []
    for bills in collection_bills.find({"status": {"$nin": excluded_statuses}}):
        vacancy_data = {
            "bill_id": bills["bill_id"],
            "category": bills["category"],
            "Date": bills["Date"],
        }
        bills_hr.append(vacancy_data)
    return bills_hr

@router.put("/update_hr_bill/{bill_id}")
def update_hr_bill(bill_id: str, status_data: UpdateVacancyStatus, current_user: User = Depends(get_current_user)):
    # Check if the current user is an HR user
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can update vacancies")

    # Check if the bill exists
    existing_bill = collection_bills.find_one({"bill_id": bill_id})
    if not existing_bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    # Update the status of the bill
    collection_bills.update_one({"bill_id": bill_id}, {"$set": {"status": status_data.new_status}})

    return {"message": f"Bill {bill_id} updated successfully"}


@router.post("/create_candidate")
def create_candidate(request_data: Candidate):
    last_candidate = collection_new_candidate.find_one(sort=[("_id", -1)])
    last_id = last_candidate["c_id"] if last_candidate else "C000"

    last_seq = int(last_id[1:])  
    new_seq = last_seq + 1

    # Format the new candidate ID
    c_id = f"C{new_seq:03d}"

    data = {
        "c_id": c_id,
        "email": request_data.email,
        "cv": "pending",
        "name": request_data.name,
        "type": request_data.type,
        "vacancy_id": request_data.vacancy_id,
        "status": "pending"
    }
    collection_new_candidate.insert_one(data)
    return {"message": "Candidate created successfully"}

@router.get("/get_candidates")
def get_candidates(current_user: User = Depends(get_current_user)):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view vacancies")

    # Define the statuses to exclude
    excluded_statuses = ["approved", "rejected"]
    candidates = []
    for candidate in collection_new_candidate.find({"status": {"$nin": excluded_statuses}}):
        candidate_data = {
            "c_id": candidate["c_id"],
            "email": candidate["email"],
            "name": candidate["name"],
            "cv": candidate["cv"],
            "vacancy_id": candidate["vacancy_id"],
        }
        candidates.append(candidate_data)
    return candidates

@router.put("/update_candidate/{c_id}")
def update_candidate(c_id: str, status_data: UpdateCandidateStatus, current_user: User = Depends(get_current_user)):
    # Check if the current user is authorized
    if not current_user or current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can update candidates")

    # Check if the candidate exists
    existing_candidate = collection_new_candidate.find_one({"c_id": c_id})
    if not existing_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Update the status of the candidate
    collection_new_candidate.update_one({"c_id": c_id}, {"$set": {"status": status_data.new_status}})

    return {"message": f"Candidate {c_id} updated successfully"}