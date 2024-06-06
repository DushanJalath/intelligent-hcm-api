
# models.py
from pydantic import BaseModel
from typing import Optional


class User_login(BaseModel):
    type: str
    email: str
    password: str
    
class TokenRefresh(BaseModel):
    refresh_token: str

class User(BaseModel):
    name:str
    contact:str
    email:str
    address:str
    password:str
    empType:str

class add_vacancy(BaseModel):
    possition: str
    pre_requisits:str
    responsibilities: str
    project_type: str
    num_of_vacancies: int
    more_details: str

class UpdateVacancyStatus(BaseModel):
    new_status: str

class W_Hours(BaseModel):
    time:str
    OTPay:float
    totalOT:float
    hour:float
    fixedOT:float
    u_id:str

class Bills(BaseModel):
    bill_id:str
    amount:float
    category:str
    u_id:str
    storename:str
    Date:str
    status:str

class Leaves(BaseModel):
    l_id:str
    totla:float
    status:bool
    remaining:int
    u_id:str

class Candidate(BaseModel):
    email:str
    cv:str
    name:str
    type:str
    c_id:str
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
    date:str
    time:str
    result:str
    venue:str
    i_id:str
    interviewer_id:str

class PredictionRequest(BaseModel):
    date: str

class PredictionResponse(BaseModel):
    date: str
    predicted_attendance: int

