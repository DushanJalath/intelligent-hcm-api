
# models.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class User_login(BaseModel):
    type: str
    email: str
    password: str
    
class TokenRefresh(BaseModel):
    refresh_token: str

class User(BaseModel):
    name:str
    contact:str
    user_email:str
    address:str
    user_pw:str
    user_type:str
    user_role:str #added new

class add_vacancy(BaseModel):
    possition: str
    pre_requisits:str
    responsibilities: str
    project_type: str
    num_of_vacancies: int
    more_details: str

class UpdateVacancyStatus(BaseModel):
    new_status: str

class OT_Work_Hours(BaseModel):
    time:str
    OTPay:float
    totalOT:float
    hour:float
    fixedOT:float
    u_id:str

class Bills(BaseModel):
    u_id:str
    amount:float
    category:str
    storename:str
    Date:str
    status:str
    submitdate:str
    invoice_number:str

#new basemodel for Employee Leaves
class EmployeeLeave(BaseModel):
    user_email:str
    name: str
    start_date: datetime
    end_date: datetime
    leave_type: str
    leave_status:str="pending"

class Leaves(BaseModel):
    l_id:str
    totla:float
    status:bool
    remaining:int
    u_id:str

class Candidate(BaseModel):
    #changed the order
    c_id:str
    email:str
    name:str
    cv:str
    score:float #addded new
    vacancy_id:str

class UpdateCandidateStatus(BaseModel):
    new_status:str


class Parsed_Candidates(BaseModel):
    candidate_id:str
    id:str
    qualifications:str
    score:str
    reason:str

class Interview(BaseModel):
    i_id:str
    c_id:str
    date:str
    time:str
    venue:str
    interviewer_id:str
    confirmed_date:str
    result:str #pending or confrim or selected or rejected
    #candidate_id:str
    

class PredictionRequest(BaseModel):
    date: str

class PredictionResponse(BaseModel):
    date: str
    predicted_attendance: int

class EmpSubmitForm(BaseModel):
    fullName:str
    eMail:str
    contact:str
    dob:str

class EmpTimeRep(BaseModel):
    email:str
    date:str
    project_type:str
    totalWorkHours:int

class FileModel(BaseModel):  
    image_url: str

      
class LeaveRequest(BaseModel):
    leaveType: str
    startDate: str
    dayCount:  str
    submitdate:str
    submitdatetime:str

class Update_leave_request(BaseModel):
    new_status: str

class EmployeeLeaveCount(BaseModel):
    submitdate: str
    sickLeaveCount: str
    casualLeaveCount: str
    annualLeaveCount:  str

class ManagerLeaveCount(BaseModel):
    submitdate:str
    sickLeaveCount: str
    casualLeaveCount: str
    annualLeaveCount:  str

class UserMessage(BaseModel):
    message: str

