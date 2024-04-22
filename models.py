
# models.py
from pydantic import BaseModel
from typing import Optional


# for login
class User_login(BaseModel):
    type: str
    email: str
    password: str

class User(BaseModel):
    user_id:str
    user_pw:str
    salary:float
    user_type:str
    address:str
    user_email:str
    project:str
    user_name:str
    contact:str
    manager_id:str   

class add_vacancy(BaseModel):
    possition: str
    pre_requisits:str
    responsibilities: str
    project_type: str
    num_of_vacancies: int
    more_details: str

class W_Hours(BaseModel):
    time:str
    OTPay:float
    totalOT:float
    hour:float
    fixedOT:float
    u_id:str

class Bills(BaseModel):
    status:bool
    bill_id:str
    amount:float
    category:float
    details:str
    u_id:str

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