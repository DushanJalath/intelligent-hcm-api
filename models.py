
# models.py
from pydantic import BaseModel

class User_login(BaseModel):
    email: str
    password: str
  