# utils.py
import bcrypt
from jose import jwt
from jose.exceptions import JWTError
from fastapi import Depends
from datetime import datetime, timedelta
from fastapi import HTTPException
from config import SECRET_KEY, ALGORITHM
from database import collection_user
from fastapi.security import OAuth2PasswordBearer
import requests
import PIL.Image
import google.generativeai as genai
from io import BytesIO


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    encoded_password = password.encode("utf-8")
    hashed = bcrypt.hashpw(encoded_password, salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    encoded_plain_password = plain_password.encode("utf-8")
    encoded_hashed_password = hashed_password.encode("utf-8")
    return bcrypt.checkpw(encoded_plain_password, encoded_hashed_password)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def authenticate_user(email: str, password: str):
    existing_user = collection_user.find_one({"user_email": email})
    if not existing_user or not verify_password(password, existing_user["user_pw"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return existing_user


async def authenticate_user_exist(email: str):
    existing_user = collection_user.find_one({"user_email": email}, {"_id": 0, "user_email": 1, "user_type": 1})
    if not existing_user:
        raise HTTPException(status_code=401, detail="Incorrect email")
    return existing_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    print("Received Token:", token)
    try:
        payload = decode_access_token(token)
        if payload is None:
            raise credentials_exception
    except:
        raise credentials_exception
    user = await authenticate_user_exist(email=payload)
    if user is None:
        raise credentials_exception
    return user

def extract_entities_from_text(billtext):
    
    url = "https://ai-textraction.p.rapidapi.com/textraction"
    payload = {
	"text": billtext
    ,
	"entities": [
		{
			"var_name": "store",
			"type": "string",
			"description": "invoice store"
		},
		{
			"var_name": "invoicenumber",
			"type": "string",
			"description": "invoice reference number"
		},
		{
			"var_name": "date",
			"type": "string",
			"description": "date"
		},
		{
			"var_name": "totalpayableamount",
			"type": "float",
			"description": "total amount in invoice"
		},
		
	]
    }
    headers = {
	"content-type": "application/json",
	"X-RapidAPI-Key": "998c96c929msh24a280d46e133afp144d06jsna115bef7f7da",
	"X-RapidAPI-Host": "ai-textraction.p.rapidapi.com"
    }
    
    res = requests.post(url, json=payload, headers=headers).json()
    data = {"storename": res['results']['store'],
    "invoicenumber": res['results']['invoicenumber'],
    "date": res['results']['date'],
    "totalamount": res['results']['totalpayableamount']
    }
    return(data)


async def fetch_and_extract_text(item):
    bill_type = item.get("bill_type")
    image_url = item.get("image_url")

    if not image_url:
        return "No image URL found."

    response = requests.get(image_url)
    img = PIL.Image.open(BytesIO(response.content))

    API_KEY = "AIzaSyDVVsp4j5iewM7hMw_h6m8oWFOIz0Fxsao"
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
    ]

     
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-pro-vision")

    response = model.generate_content([
        # "this is a bill. i need text about customer name, customer address, total amount, billing details and dates, total amount, date, receipt id, organization name,invoice number. extract that text and can you give output as paragraph.",
        # img
         "this is a bill. i need extract about customer name, customer address, total amount, billing dates, total amount, receipt id, organization name,invoice number.If you can't extract all the datas try to get invoice number,dates and customer name",
        img
    ], safety_settings=safety_settings, stream=True)

    try:
        response.resolve()
        extracted_text = response.text if len(response.text.split("\n")) > 1 else "No text extracted."
    except Exception as e:
        extracted_text = "Error during text extraction. Please try it Manually."

    return extracted_text

async def extract_text_from_images(images):
    results = []
    for image_data in images:
        extracted_text = await fetch_and_extract_text(image_data)
        results.append({"bill_type": image_data.get("bill_type"), "extracted_text": extracted_text})

    return results

def convert_object_id(doc):
    doc['_id'] = str(doc['_id'])
    return doc
