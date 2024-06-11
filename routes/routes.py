from fastapi import APIRouter, Depends, HTTPException, File, UploadFile,Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta
from models import EmpTimeRep, EmpSubmitForm,User_login, User, add_vacancy, UpdateVacancyStatus, Bills, Candidate, UpdateCandidateStatus,FileModel
from utils import get_current_user
from config import ACCESS_TOKEN_EXPIRE_MINUTES
from gridfs import GridFS
from bson.objectid import ObjectId
from gridfs import GridFS
from services import (
    login_user,
    refresh_tokens,
    create_new_user,
    login_user_manual,
    create_new_vacancy,
    get_all_vacancies,
    get_hr_vacancies_service,
    update_hr_vacancy_status,
    create_new_bill,
    get_user_bill_status,
    get_hr_bills_service,
    get_bill_pdf,
    update_hr_bill_status,
    create_new_candidate,
    get_candidates_service,
    update_candidate_status,
    upload_cvs,
    download_candidate_cv,
    get_gridfs,
    empSubmitForm,
    empTimeReport,
    upload_bills
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    return await login_user(form_data, ACCESS_TOKEN_EXPIRE_MINUTES)  # Ensure async function is awaited

@router.post("/refresh_token")
async def refresh_access_token(refresh_token: str):
    return refresh_tokens(refresh_token)

@router.post("/users")
async def create_user(user: User):
    return create_new_user(user)

@router.post("/login")
async def login(user_login: User_login):
    return login_user_manual(user_login, ACCESS_TOKEN_EXPIRE_MINUTES)

@router.post("/create_vacancy")
def create_vacancy(request_data: add_vacancy, current_user: User = Depends(get_current_user)):
    return create_new_vacancy(request_data, current_user)

@router.get("/get_vacancies")
def get_vacancies(current_user: User = Depends(get_current_user)):
    return get_all_vacancies(current_user)

@router.get("/profile")
def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/get_hr_vacancies")
def get_hr_vacancies(current_user: User = Depends(get_current_user)):
    return get_hr_vacancies_service(current_user)

@router.put("/update_hr_vacancy/{vacancy_id}")
def update_hr_vacancy(vacancy_id: str, status_data: UpdateVacancyStatus, current_user: User = Depends(get_current_user)):
    return update_hr_vacancy_status(vacancy_id, status_data, current_user)

@router.post("/upload-bill/")
async def upload_bill_route(file: UploadFile = File(...),current_user: User = Depends(get_current_user)):
    return await upload_bills(file)

@router.post("/create_bill")
def create_bill(request_data: Bills, current_user: User = Depends(get_current_user)):
    return create_new_bill(request_data, current_user)

@router.get("/bill_status")
def get_bill_status(current_user: User = Depends(get_current_user)):
    return get_user_bill_status(current_user)


@router.get("/get_hr_bills")
def get_hr_bills(current_user: User = Depends(get_current_user)):
    return get_hr_bills_service(current_user)

@router.put("/update_hr_bill/{bill_id}")
def update_hr_bill(bill_id: str, status_data: UpdateVacancyStatus, current_user: User = Depends(get_current_user)):
    return update_hr_bill_status(bill_id, status_data, current_user)

@router.get("/get_bill_pdf/{bill_id}")
def get_billpdf(bill_id: str,current_user: User = Depends(get_current_user)):
    return get_bill_pdf(bill_id,current_user)

@router.post("/create_candidate")
def create_candidate(request_data: Candidate):
    return create_new_candidate(request_data)

@router.get("/get_candidates")
def get_candidates(current_user: User = Depends(get_current_user)):
    return get_candidates_service(current_user)

@router.put("/update_candidate/{c_id}")
def update_candidate(c_id: str, status_data: UpdateCandidateStatus, current_user: User = Depends(get_current_user)):
    return update_candidate_status(c_id, status_data, current_user)

@router.post("/upload_cv/{c_id}")
async def upload_cv(c_id: str, file: UploadFile = File(...)):
    return upload_cvs(c_id, file)

@router.get("/download_cv/{cv_id}")
async def download_cv(cv_id: str, fs: GridFS = Depends(get_gridfs), current_user: User = Depends(get_current_user)):
    return download_candidate_cv(cv_id, fs, current_user)

@router.post("/empSubmit")
async def empSubmit(form:EmpSubmitForm):
    return empSubmitForm(form)

@router.post('/empTimeReport')
async def empTimeRep(data:EmpTimeRep):
    return empTimeReport(data)
