# services.py
from database import fs_pic, collection_emp_time_rep, collection_user, collection_add_vacancy, collection_bills, collection_new_candidate, fs,collection_emp_vac_submit,collection_bill_upload
from models import UserResponse,TimeReportQuery, EmpTimeRep, EmpSubmitForm, User, add_vacancy, Bills, Candidate, UpdateVacancyStatus, UpdateCandidateStatus,FileModel
from utils import convert_object_id, hash_password, verify_password, create_access_token, create_refresh_token, authenticate_user,decode_token,extract_entities_from_text,extract_text_from_images
from datetime import timedelta
from typing import List
from pymongo.collection import Collection
from bson import ObjectId
from gridfs import GridFS
from fastapi import HTTPException, UploadFile, File, Response
from fastapi.responses import StreamingResponse
from config import REFRESH_TOKEN_EXPIRE_DAYS,ACCESS_TOKEN_EXPIRE_MINUTES
from reportlab.pdfgen import canvas 
from reportlab.pdfbase.ttfonts import TTFont 
from reportlab.pdfbase import pdfmetrics 
from reportlab.lib import colors 
from reportlab.lib.pagesizes import letter
import io ,os
import io ,os
from google.cloud import storage
import aiohttp
from bson import json_util
import json


def get_gridfs():
    return fs

async def login_user(form_data, access_token_expire_minutes):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token_expires = timedelta(minutes=access_token_expire_minutes)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(data={"email": user['user_email']}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"email": user["user_email"]}, expires_delta=refresh_token_expires)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

def refresh_tokens(refresh_token: str):
    payload = decode_token(refresh_token)
    email = payload.get("email")
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(data={"email": email}, expires_delta=access_token_expires)
    return {"access_token": new_access_token, "token_type": "bearer"}

async def create_new_user(user: User, file: UploadFile) -> UserResponse:
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    file_extension = file.filename.split('.')[-1]
    if file_extension.lower() not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Only PNG and JPG files are allowed.")

    bucket_name = "pdf_save"
    credentials_path = "D:/BSc Hons. in AI/Level 2 Sem 2/CM2900 - Industry Based AI Software Project/Codes/intelligent-hcm-api/t.json"
    client = storage.Client.from_service_account_json(credentials_path)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file.filename)
    blob.upload_from_string(await file.read(), content_type=file.content_type)

    image_url = f"https://storage.googleapis.com/{bucket_name}/{file.filename}"
    hashed_password = hash_password(user.user_pw)
    user_data = user.dict()
    user_data["user_pw"] = hashed_password
    user_data['profile_pic_url'] = image_url
    result =  collection_user.insert_one(user_data)
    
    return UserResponse(message="User created successfully", user_id=str(result.inserted_id))

def login_user_manual(user_login, ACCESS_TOKEN_EXPIRE_MINUTES):
    existing_user = collection_user.find_one(
        {"user_email": user_login.email},
        {"_id": 0, "user_email": 1, "user_pw": 1, "user_type": 1}
    )
    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(user_login.password, existing_user["user_pw"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"email": user_login.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "type": existing_user.get("user_type")}

def create_new_vacancy(request_data, current_user):
    last_vacancy = collection_add_vacancy.find_one(sort=[("_id", -1)])
    last_id = last_vacancy["vacancy_id"] if last_vacancy else "A000"
    last_seq = int(last_id[1:])
    new_seq = last_seq + 1
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
        "publish_status": "pending",
    }
    collection_add_vacancy.insert_one(data)
    return {"message": "Vacancy created successfully"}

def get_all_vacancies(current_user):
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

def get_hr_vacancies_service(current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view vacancies")
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

def update_hr_vacancy_status(vacancy_id, status_data, current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can update vacancies")
    existing_vacancy = collection_add_vacancy.find_one({"vacancy_id": vacancy_id})
    if not existing_vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    collection_add_vacancy.update_one({"vacancy_id": vacancy_id}, {"$set": {"status": status_data.new_status}})
    return {"message": f"Vacancy {vacancy_id} updated successfully"}

async def upload_bills(file: UploadFile):
    global global_image_url
    try:
        allowed_extensions = {'png', 'jpg', 'jpeg'}
        file_extension = file.filename.split('.')[-1]
        if file_extension.lower() not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Only PNG and JPG files are allowed.")

        bucket_name = "pdf_save"
        credentials_path = "D:/json key/t.json"
        client = storage.Client.from_service_account_json(credentials_path)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file.filename)
        blob.upload_from_string(await file.read(), content_type=file.content_type)

        image_url = f"https://storage.googleapis.com/{bucket_name}/{file.filename}"
        file_doc = FileModel(image_url=image_url)
        global_image_url = image_url

        collection_bill_upload.insert_one(file_doc.dict())

        extracted_text = await extract_text_from_images([file_doc.dict()])
        
        billtext = extracted_text[0]["extracted_text"]
         
        bill_entities = await extract_bill_entity(image_url, billtext)

     
        return {"message": "File uploaded successfully","file_url": image_url, "billtext": billtext, "bill_entities": bill_entities}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to upload file. Please try again.")

async def extract_bill_entity(image_url, text):
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if response.status != 200:
                return {"error": "Failed to download image"}
            image_content = await response.read()
            
    with open("invoiceimage.jpg", "wb") as temp_file:
        temp_file.write(image_content)

    return extract_entities_from_text(text)

def create_new_bill(request_data, current_user):
    global global_image_url
    last_bill = collection_bills.find_one(sort=[("_id", -1)])
    last_id = last_bill["bill_id"] if last_bill else "B000"
    last_seq = int(last_id[1:])
    new_seq = last_seq + 1
    bill_id = f"B{new_seq:03d}"
    data = {
        "bill_id": bill_id,
        "user_type": current_user.get('user_type'),
        "user_email": current_user.get("user_email"),
        "amount": request_data.amount,
        "category": request_data.category,
        "storename": request_data.storename,
        "Date": request_data.Date,
        "status": "pending",
        "submitdate": request_data.submitdate,
        "invoice_number": request_data.invoice_number,
        "image_url": global_image_url
    }
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Invoice Details")
    c.drawString(100, 700, f"BillID: {data['bill_id']}")
    c.drawString(100, 670, f"Useremail: {data['user_email']}")
    c.drawString(100, 640, f"Category: {data['category']}")
    c.drawString(100, 610, f"Store Name: {data['storename']}")
    c.drawString(100, 580, f"Amount: {data['amount']}")
    c.drawString(100, 550, f"Date: {data['Date']}")
    c.drawString(100, 520, f"Invoice Number: {data['invoice_number']}")
    image_path = 'invoiceimage.jpg' 
    c.drawImage(image_path, 150, 100, width=300, height=300)
    c.save()
    pdf_content = buffer.getvalue()
    data['pdf_content'] = pdf_content
    collection_bills.insert_one(data)
    os.remove(image_path)
    return {"message": "Bill created successfully"}

def get_user_bill_status(current_user):
    if current_user.get('user_type') not in ["HR", "Manager" ,"Employee"]:
        raise HTTPException(status_code=403, detail="Unauthorized, only Employees can upload bills")
    try:
        cursor = collection_bills.find(
        {"user_email": current_user.get('user_email')},
        {"category": 1, "submitdate": 1, "status": 1, "_id": 0}
        )
        results = list(cursor)
        if not results:
            raise HTTPException(status_code=404, detail="No bills found for the given employee ID")
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_hr_bills_service(current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view bills")
    excluded_statuses = ["approved", "rejected"]
    bills_hr = []
    for bills in collection_bills.find({"status": {"$nin": excluded_statuses}}):
        bills_data = {
            "bill_id": bills["bill_id"],
            "category": bills["category"],
            "Date": bills["submitdate"],
        }
        bills_hr.append(bills_data)
    return bills_hr

def get_bill_pdf(bill_id,current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view bills")
    document = collection_bills.find_one({'bill_id': bill_id})
    pdf_data = document['pdf_content']
    return Response(content=pdf_data, media_type='application/pdf')

def update_hr_bill_status(bill_id, status_data, current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can update bills")
    existing_bill = collection_bills.find_one({"bill_id": bill_id})
    if not existing_bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    collection_bills.update_one({"bill_id": bill_id}, {"$set": {"status": status_data.new_status}})
    return {"message": f"Bill {bill_id} updated successfully"}


async def get_bill_details(collection_bills: Collection, user_email: str) -> List[dict]:
    try:
        bills = collection_bills.find({"user_email": user_email})
        bill_details = []
        for bill in bills:
            bill_details.append({
                "category": bill.get("category"),
                "status": bill.get("status"),
                "submitdate": bill.get("submitdate"),
                "image_url": bill.get("image_url"),
                "invoice_number": bill.get("invoice_number"),
                "total_amount": bill.get("total_amount"),
            })
        return bill_details
    except Exception as e:
        # Consider logging the error instead of printing it
        print(e)
        raise HTTPException(status_code=500, detail="Failed to retrieve bill details")


def create_new_candidate(request_data):
    last_candidate = collection_new_candidate.find_one(sort=[("_id", -1)])
    last_id = last_candidate["c_id"] if last_candidate else "C000"
    last_seq = int(last_id[1:])
    new_seq = last_seq + 1
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

def get_candidates_service(current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view candidates")
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

def update_candidate_status(c_id, status_data, current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can update candidates")
    existing_candidate = collection_new_candidate.find_one({"c_id": c_id})
    if not existing_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    collection_new_candidate.update_one({"c_id": c_id}, {"$set": {"status": status_data.new_status}})
    return {"message": f"Candidate {c_id} updated successfully"}

def upload_cvs(c_id, file):
    try:
        # Save the uploaded file to GridFS
        cv_id = fs.put(file.file, filename=file.filename)

        # Update the candidate document in the database with the new cv_id
        collection_new_candidate.update_one({"c_id": c_id}, {"$set": {"cv": str(cv_id)}})

        return {"cv_id": str(cv_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def download_candidate_cv(cv_id, fs, current_user):
    if current_user.get('user_type') not in ["HR", "Manager"]:
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can download CVs")
    try:
        # Retrieve the file from GridFS
        file = fs.get(ObjectId(cv_id))
        if file is None:
            raise HTTPException(status_code=404, detail="CV not found")
        # Return the file content as a StreamingResponse with the original filename
        return StreamingResponse(file, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={file.filename}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def empSubmitForm(form:EmpSubmitForm):
    existing_user = collection_user.find_one({"user_email": form.eMail})
    if not existing_user:
        raise HTTPException(status_code=400, detail="Invalid Email")
    form_data = form.dict()
    inserted_user = collection_emp_vac_submit.insert_one(form_data)
    return {"message": "Form Submitted successfully", "user_id": str(inserted_user.inserted_id)}

def empTimeReport(timeRep:EmpTimeRep,current_user):
    existing_user = collection_user.find_one({"user_email": current_user.get("user_email")})
    data={
        "user_email":current_user.get("user_email"),
        "date":timeRep.date,
        "project_type":timeRep.project_type,
        "totalWorkMilliSeconds":timeRep.totalWorkMilliSeconds,
    }
    if not existing_user:
        raise HTTPException(status_code=400, detail="Invalid Email")
    form_data = timeRep.dict()
    inserted_user = collection_emp_time_rep.insert_one(data)
    return {"message": "Time Reported Success fully", "user_id": str(inserted_user.inserted_id)}

def get_total_work_time(query:TimeReportQuery,current_user):
    try:
        # MongoDB query
        result = collection_emp_time_rep.aggregate([
            {
                "$match": {
                    "user_email": current_user.get("user_email"),
                    "date": query.date
                }
            },
            {
                "$group": {
                    "_id": None,
                    "totalMilliseconds": { "$sum": "$totalWorkMilliSeconds" }
                }
            }
        ])
        
        # Convert the result to a list and get the total milliseconds
        result_list = list(result)
        if result_list:
            total_milliseconds = result_list[0]["totalMilliseconds"]
        else:
            total_milliseconds = 0

        return {"totalTime":total_milliseconds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def get_user_details(user):
    result = collection_user.find_one({"user_email": user.get('user_email')})
    if user:
        result = convert_object_id(result)
        return json.loads(json_util.dumps(result))
    else:
        raise HTTPException(status_code=404, detail="User not found")