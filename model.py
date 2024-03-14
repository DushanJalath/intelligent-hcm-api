from pydantic import BaseModel

class User(BaseModel):
    id:str
    pw:str
    salary:float
    type:str
    address:str
    email:str
    project:str
    name:str
    contact:str
    manager_id:str

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

class Vacancy(BaseModel):
    position:str
    description:str
    pre_requisits:str
    responsibilities:str
    noOfVacancies:int
    remote_physical:str
    name:str
    project:str
    v_id:str

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