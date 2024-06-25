from fastapi import APIRouter, Depends, HTTPException, File, UploadFile,Form,Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from datetime import timedelta
from models import EmpTimeRep, EmpSubmitForm,User_login, User, add_vacancy, UpdateVacancyStatus, Bills, Candidate, UpdateCandidateStatus,FileModel,LeaveRequest,Update_leave_request,EmployeeLeaveCount,ManagerLeaveCount
from utils import get_current_user
from config import ACCESS_TOKEN_EXPIRE_MINUTES
from gridfs import GridFS
from bson.objectid import ObjectId
from gridfs import GridFS
from typing import List
from database import collection_bills,collection_user
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
    upload_bills,
    get_bill_details,
    get_user_details,
    create_user_leave_request,
    calculate_leave_difference,
    pass_employee_leave_count,
    get_user_total_leave_days,
    pass_manager_leave_count,
    pass_employee_leave_request,
    get_user_leave_request,
    get_user_leave_status,
    get_hr_leave_service,
    update_hr_leave_status,
    create_manager_leave_count,
    get_manager_leave_count,
    create_employee_leave_count,
    get_employee_leave_count,
    get_user_leave_report,
    generate_pdf
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


@router.get("/bill-details")
async def get_bill_details_route(current_user_email: str = Depends(get_current_user)):
    bill_details = await get_bill_details(collection_bills, current_user_email["user_email"])
    return JSONResponse(content={"bill_details": bill_details}, status_code=200)

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

@router.get("/current-user-details")
async def get_current_user_details(current_user_email: str = Depends(get_current_user)):
    user_details = await get_user_details(collection_user, current_user_email["user_email"])
    return user_details


@router.get("/leave_report")
async def get_leave_report(email: str = None, current_user: User = Depends(get_current_user)):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view leave reports")

    leave_reports = get_user_leave_report(email)
    pdf = generate_pdf(leave_reports)
    
    filename = f"leave_report_{email}.pdf" if email else "leave_report_all.pdf"

    response = Response(content=pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@router.post("/create_leave_request")
async def create_leave_request(request_data: LeaveRequest, current_user_details: dict = Depends(get_current_user_details)):
    return await create_user_leave_request(request_data, current_user_details)


#Hr accept or reject leave requests
@router.put("/update_hr_leave/{leave_id}")
async def update_hr_leave(leave_id: str, status_data: Update_leave_request, current_user: User = Depends(get_current_user)):
    return update_hr_leave_status(leave_id, status_data, current_user)


#get pending status leave requests
@router.get("/get_hr_leave")
async def get_hr_leave(current_user: User = Depends(get_current_user)):
    return get_hr_leave_service(current_user)


#get details about own leave
@router.get("/leave_status")
async def get_leave_status(current_user: User = Depends(get_current_user)):
    return get_user_leave_status(current_user)


#user can get own leave requets
@router.get("/get_leave_request")
async def get_leave_request(current_user: User = Depends(get_current_user)):
    return get_user_leave_request(current_user)


# Get Employees Remaning Leave Count
@router.get("/employee_remaning_leaves", response_model=dict)
async def get_employee_remaning_leaves(current_user_details: dict = Depends(get_current_user_details)):
    difference = await calculate_leave_difference(current_user_details)
    return difference


# Get Used Leave Count
@router.get("/get_total_leave_days")
async def get_total_leave_days(current_user_details: dict = Depends(get_current_user_details)):
    return get_user_total_leave_days(current_user_details)


# Get Employee Latest Leave Count
@router.get("/pass_employee_leave_count", response_model=List[dict])
async def pass_employee_leave_request(current_user_details: dict = Depends(get_current_user_details)):
    return pass_employee_leave_count(current_user_details)


# Get Employee Leave Count
@router.get("/get_employee_leave_count")
async def get_employee_leave_request(current_user_details: dict = Depends(get_current_user_details)):
    return get_employee_leave_count(current_user_details)


# Set Employee Leave Count
@router.post("/employee_leave_count")
async def employee_leave_count(request_data: EmployeeLeaveCount, current_user: User = Depends(get_current_user)):
    return create_employee_leave_count(request_data, current_user)


# Set Manager Leave Count
@router.post("/manager_leave_count")
async def manager_leave_count(request_data: ManagerLeaveCount, current_user: User = Depends(get_current_user)):
    return create_manager_leave_count(request_data, current_user)


# Get Manager Leave Count
@router.get("/get_manager_leave_count")
async def get_manager_leave_request(current_user_details: dict = Depends(get_current_user_details)):
    return get_manager_leave_count(current_user_details)


# # Get Manager Latest Leave Count
# @router.get("/pass_manager_leave_count", response_model=List[dict])
# async def pass_manager_leave_request(current_user_details: dict = Depends(get_current_user_details)):
#     return pass_manager_leave_count(current_user_details)




