# services.py
from database import collection_emp_time_rep, collection_user, collection_add_vacancy, collection_bills, collection_new_candidate, fs,collection_emp_vac_submit,collection_bill_upload,collection_interviews,collection_leaves,collection_remaining_leaves,collection_working_hours,collection_add_leave_request,collection_add_employee_leave_count,collection_add_manager_leave_count,collection_job_vacancies,grid_fs,collection_job_applications
from models import UserResponse,TimeReportQuery, EmpTimeRep, EmpSubmitForm, User, add_vacancy, Bills, Candidate, UpdateVacancyStatus, UpdateCandidateStatus,FileModel,JobVacancy,JobApplicatons
from utils import convert_object_id, hash_password, verify_password, create_access_token, create_refresh_token, authenticate_user,decode_token,extract_entities_from_text,extract_text_from_images,get_current_user
from datetime import timedelta
from typing import List
from pymongo.collection import Collection
from bson import ObjectId
from gridfs import GridFS
from fastapi import HTTPException, UploadFile, File, Response,Depends
from fastapi.responses import StreamingResponse
from config import REFRESH_TOKEN_EXPIRE_DAYS,ACCESS_TOKEN_EXPIRE_MINUTES
from reportlab.pdfgen import canvas 
from reportlab.pdfbase.ttfonts import TTFont 
from reportlab.pdfbase import pdfmetrics 
from reportlab.lib import colors 
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from cv_parser import process_resume
import PyPDF2
import io ,os
import io ,os
from google.cloud import storage
import aiohttp
from bson import json_util,ObjectId  
from pymongo import MongoClient, DESCENDING
from io import BytesIO
from starlette.responses import JSONResponse,StreamingResponse
from reportlab.lib.utils import ImageReader
from PIL import Image
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
    return {"access_token": access_token, "type": existing_user.get("user_type"), "email": existing_user.get("user_email")}

def create_new_vacancy(request_data, current_user):
    last_vacancy = collection_add_vacancy.find_one(sort=[("_id", -1)])
    last_id = last_vacancy["vacancy_id"] if last_vacancy else "A000"
    last_seq = int(last_id[1:])
    new_seq = last_seq + 1
    vacancy_id = f"A{new_seq:03d}"
    
    # Generate PDF
    pdf_file_path = generate_vacancy_pdf(request_data.possition, request_data.job_type, request_data.pre_requisits, request_data.responsibilities, request_data.more_details)
    
    # Store PDF in GridFS
    pdf_file_id = store_pdf_in_gridfs(pdf_file_path, f"{vacancy_id}.pdf")
    
    # Remove the local file after storing it in GridFS
    os.remove(pdf_file_path)

    # Convert pdf_file_id to string (removes the ObjectID wrapper)
    pdf_file_id_str = str(pdf_file_id)
    
    data = {
        "vacancy_id": vacancy_id,
        "user_type": current_user.get('user_type'),
        "user_email": current_user.get("user_email"),
        "job_type": request_data.job_type,
        "pre_requisits": request_data.pre_requisits,
        "possition": request_data.possition,
        "num_of_vacancies": request_data.num_of_vacancies,
        "responsibilities": request_data.responsibilities,
        "work_mode": request_data.work_mode,
        "more_details": request_data.more_details,
        "status": "pending",
        "publish_status": "pending",
        "pdf_file_id": pdf_file_id_str  # Store the pdf_file_id as string
    }
    collection_add_vacancy.insert_one(data)
    
    return {"message": "Vacancy created successfully", "pdf_file_id": pdf_file_id_str}

def generate_vacancy_pdf(position, job_type, pre_requisites, responsibilities, more_details):
    file_name = "vacancy_details.pdf"
    c = canvas.Canvas(file_name, pagesize=letter)
    width, height = letter
    
    # Set the logo path to the images folder
    logo_path = "newLogo.png"
    
    # Load the image using Pillow and ensure transparency is handled
    image = Image.open(logo_path)
    if image.mode in ('RGBA', 'LA'):
        background = Image.new(image.mode[:-1], image.size, (255, 255, 255))
        background.paste(image, image.split()[-1])
        image = background
    
    logo = ImageReader(image)
    logo_width, logo_height = 100, 100  # Adjust size as needed
    c.drawImage(logo, 20, height - logo_height - 20, width=logo_width, height=logo_height)
    
    # Add position and job type to the right side of the logo
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 20, height - 50, f"Job Position: {position}")
    c.drawRightString(width - 20, height - 70, f"Job Type: {job_type}")
    
    # Text settings
    text_margin = 50  # Margin from the left edge
    line_height = 12
    max_line_length = 110  # Maximum characters per line for other sections
    max_line_length_more_details = 60  # Maximum characters per line for more_details

    # Add Company Description
    company_description = """IFS is a billion-dollar revenue company with 6000+ employees on all continents. Our leading AI technology 
    is the backbone of our award-winning enterprise software solutions, enabling our customers to be their 
    best when it really matters–at the Moment of Service™. Our commitment to internal AI adoption has allowed 
    us to stay at the forefront of technological advancements,ensuring our colleagues can unlock their creativity 
    and productivity, and our solutions are always cutting-edge.

    At IFS, we’re flexible, we’re innovative, and we’re focused not only on how we can engage with our customers 
    but on how we can make a real change and have a worldwide impact. We help solve some of society’s greatest 
    challenges, fostering a better future through our agility, collaboration, and trust.

    We celebrate diversity and understand our responsibility to reflect the diverse world we work in. We are 
    committed to promoting an inclusive workforce that fully represents the many different cultures, backgrounds, 
    and viewpoints of our customers, our partners,and our communities. As a truly international company serving 
    people from around the globe, we realize that our success is tantamount to the respect we have for those 
    different points of view.

    By joining our team, you will have the opportunity to be part of a global, diverse environment; you will be 
    joining a winning team with a commitment to sustainability; and a company where we get things done so that 
    you can make a positive impact on the world.

    We’re looking for innovative and original thinkers to work in an environment where you can #MakeYourMoment 
    so that we can help others make theirs. With the power of our AI-driven solutions, we empower our team to 
    change the status quo and make a real difference.

    If you want to change the status quo, we’ll help you make your moment. Join Team Purple. Join IFS."""
    
    # Draw the company description on the PDF
    c.drawString(text_margin, height - 140, "Company Description")
    c.setFont("Helvetica", 10)
    
    # Splitting the company description into lines and drawing each line
    company_description_lines = company_description.split('\n')
    y_position = height - 160  # Starting y position for the text
    for paragraph in company_description_lines:
        lines = paragraph.split('\n')
        for line in lines:
            if y_position < 50:
                c.showPage()
                y_position = height - 50
                c.setFont("Helvetica", 10)
            c.drawString(text_margin, y_position, line)
            y_position -= line_height
    
    # Add top margin for "Pre-requisites:"
    top_margin_pre_requisites = 140 + len(company_description_lines) * line_height + 40  # Adjust this value as needed
    
    # Pre-requisites
    c.setFont("Helvetica-Bold", 12)
    c.drawString(text_margin, y_position - 20, "Pre-requisites")
    y_position -= 40
    c.setFont("Helvetica", 10)
    pre_requisites_lines = pre_requisites.split('\n')
    for line in pre_requisites_lines:
        if y_position < 50:
            c.showPage()
            y_position = height - 50
            c.setFont("Helvetica", 10)
        c.drawString(text_margin, y_position, line)
        y_position -= line_height
    
    # Responsibilities
    c.setFont("Helvetica-Bold", 12)
    c.drawString(text_margin, y_position - 20, "Responsibilities")
    y_position -= 40
    c.setFont("Helvetica", 10)
    responsibilities_lines = responsibilities.split('\n')
    for line in responsibilities_lines:
        if y_position < 50:
            c.showPage()
            y_position = height - 50
            c.setFont("Helvetica", 10)
        c.drawString(text_margin, y_position, line)
        y_position -= line_height
    
    # More Details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(text_margin, y_position - 20, "More Details")
    y_position -= 40
    c.setFont("Helvetica", 10)
    more_details_lines = more_details.split('\n')
    for line in more_details_lines:
        if y_position < 50:
            c.showPage()
            y_position = height - 50
            c.setFont("Helvetica", 10)
        c.drawString(text_margin, y_position, line)
        y_position -= line_height
    
    c.showPage()
    c.save()
    
    return file_name

def store_pdf_in_gridfs(file_path, file_name):
    with open(file_path, 'rb') as f:
        file_id = fs.put(f, filename=file_name)
    return file_id
    

def get_all_vacancies(current_user):
    vacancies = []
    for vacancy in collection_add_vacancy.find({"user_email": current_user.get("user_email")}):
        vacancy_data = {
            "vacancy_id": vacancy["vacancy_id"],
            "job_type": vacancy["job_type"],
            "possition": vacancy["possition"],
            "num_of_vacancies": vacancy["num_of_vacancies"],
            "status": vacancy["status"],
            "publish_status": vacancy["publish_status"],
            "pdf_file_id": str(vacancy["pdf_file_id"]) if isinstance(vacancy["pdf_file_id"], ObjectId) else vacancy["pdf_file_id"]
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
            "job_type": vacancy["job_type"],
            "possition": vacancy["possition"],
            "num_of_vacancies": vacancy["num_of_vacancies"],
            "pdf_file_id": str(vacancy["pdf_file_id"]) if isinstance(vacancy["pdf_file_id"], ObjectId) else vacancy["pdf_file_id"]
            
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

def publish_vacancy_service(vacancy_id: str, current_user: dict):
    vacancy = collection_add_vacancy.find_one({"vacancy_id": vacancy_id})
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    if current_user.get('user_type') != 'HR':  # Ensure only HR can publish
        raise HTTPException(status_code=403, detail="Permission denied")

    if vacancy.get('status') != 'approved':
        raise HTTPException(status_code=400, detail="Vacancy not approved yet or rejected")

    collection_add_vacancy.update_one(
        {"vacancy_id": vacancy_id},
        {"$set": {"publish_status": "approved"}}
    )

    return {"message": "Vacancy published successfully"}

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
    
    for candidate in collection_new_candidate.find({"status": {"$nin": excluded_statuses}}).sort("score", -1):
        vacancy = collection_add_vacancy.find_one({"vacancy_id": candidate["vacancy_id"]})
        if vacancy:
            candidate_data = {
                "c_id": candidate["c_id"],
                "email": candidate["email"],
                "name": candidate["name"],
                "score": candidate["score"],
                "cv": candidate["cv"],
                "vacancy": vacancy.get("possition")
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

async def get_user_detail(collection_user: Collection, user_email: str) -> dict:
    try:
        user = collection_user.find_one({"user_email": user_email}) 
        if user:
            return {
                "name": user.get("name"),
                "user_type": user.get("user_type"),
                "user_email": user.get("user_email")
            }
        else:
            return {}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to retrieve user details")


async def create_user_leave_request(request_data, current_user_details):
    last_leave_request = collection_add_leave_request.find_one(sort=[("_id", -1)])
    last_id = last_leave_request["leave_id"] if last_leave_request else "L000"
    last_seq = int(last_id[1:])
    new_seq = last_seq + 1
    leave_id = f"B{new_seq:03d}"

    if current_user_details:
        # Calculate remaining leaves dynamically
        remaining_leaves = await calculate_leave_difference(current_user_details)

        leave_request_data = {
            "leave_id": leave_id,
            "user_type": current_user_details.get('user_type'),
            "user_email": current_user_details.get("user_email"),
            "user_name": current_user_details.get("name"),
            "leaveType": request_data.leaveType,
            "startDate": request_data.startDate,
            "dayCount": request_data.dayCount,
            "submitdate": request_data.submitdate,
            "submitdatetime": request_data.submitdatetime,
            "status": "pending",
            "remaining_sick_leave": remaining_leaves.get("SickLeaveCount"),
            "remaining_annual_leave": remaining_leaves.get("AnnualLeaveCount"),
            "remaining_casual_leave": remaining_leaves.get("CasualLeaveCount")
        }

        # Insert the leave request into the database
        collection_add_leave_request.insert_one(leave_request_data)
        return {"message": "Leave request created successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

async def get_current_user_details(current_user_email: str = Depends(get_current_user)):
    user_details = await get_user_details(collection_user, current_user_email["user_email"])
    return user_details

async def pass_employee_leave_request(current_user_details: dict = Depends(get_current_user_details)):
    return pass_employee_leave_count(current_user_details)

async def get_total_leave_days(current_user_details: dict = Depends(get_current_user_details)):
    return get_user_total_leave_days(current_user_details)

async def calculate_leave_difference(current_user_details: dict) -> dict:
    pass_leave_count = await pass_employee_leave_request(current_user_details)
    total_leave_days = await get_total_leave_days(current_user_details)
    
    difference = {}

    # Convert counts to integers before calculating differences
    pass_sick_leave_count = int(pass_leave_count[0]["sickLeaveCount"])
    pass_annual_leave_count = int(pass_leave_count[0]["annualLeaveCount"])
    pass_casual_leave_count = int(pass_leave_count[0]["casualLeaveCount"])

    total_sick_leave_count = total_leave_days["leave_counts"].get("Sick Leave", 0)
    total_annual_leave_count = total_leave_days["leave_counts"].get("Annual Leave", 0)
    total_casual_leave_count = total_leave_days["leave_counts"].get("Casual Leave", 0)

    # Calculate differences
    difference["SickLeaveCount"] = pass_sick_leave_count - total_sick_leave_count
    difference["AnnualLeaveCount"] = pass_annual_leave_count - total_annual_leave_count
    difference["CasualLeaveCount"] = pass_casual_leave_count - total_casual_leave_count

    return difference

# async def get_current_user_details():

# async def pass_employee_leave_request(current_user_details: dict):

# async def get_total_leave_days(current_user_details: dict):



def pass_employee_leave_count(current_user_details):
    e_leave_count = []
    latest_leave_count = collection_add_employee_leave_count.find().sort("submitdate", DESCENDING).limit(1)
    
    for count in latest_leave_count:
        e_count_data = {
            "sickLeaveCount": count.get("sickLeaveCount"),
            "annualLeaveCount": count.get("annualLeaveCount"),
            "casualLeaveCount": count.get("casualLeaveCount"),
            "submitdate": count.get("submitdate"),
        }
        e_leave_count.append(e_count_data)    
    return e_leave_count


def pass_manager_leave_count(current_user_details):
    m_leave_count = []
    latest_leave_count = collection_add_manager_leave_count.find().sort("submitdate", DESCENDING).limit(1)
    
    for count in latest_leave_count:
        m_count_data = {
            "sickLeaveCount": count.get("sickLeaveCount"),
            "annualLeaveCount": count.get("annualLeaveCount"),
            "casualLeaveCount": count.get("casualLeaveCount"),
            "submitdate": count.get("submitdate"),
        }
        m_leave_count.append(m_count_data)    
    return m_leave_count


def get_user_total_leave_days(current_user_details):    
    user_email = current_user_details["user_email"]
    leave_types = ["Sick Leave", "Annual Leave", "Casual Leave"]
    
    leave_counts = {}
    for leave_type in leave_types:
        leave_requests = collection_add_leave_request.find({
            "user_email": user_email,
            "leaveType": leave_type,
            "status": "approved"
        })

        total_days = 0
        for leave_request in leave_requests:
            day_count = int(leave_request["dayCount"])
            total_days += day_count
        leave_counts[leave_type] = total_days

    for leave_type in leave_types:
        if leave_type not in leave_counts:
            leave_counts[leave_type] = 0

    return {"user_email": user_email, "leave_counts": leave_counts}


def get_user_leave_request(current_user_details):
    excluded_statuses = ["approved", "rejected"]
    leave_requests = []
    for request in collection_add_leave_request.find({"status": {"$nin": excluded_statuses}}):
        requested_leave_data = {
            "leave_id": request["leave_id"],
            "user_type": request["user_type"],
            "user_name": request["user_name"],
            "user_email": request["user_email"],
            "leaveType": request["leaveType"],
            "startDate": request["startDate"],
            "dayCount": request["dayCount"],
            "submitdate": request["submitdate"],            
            "status": "pending",
            "sick_leave_count": request["remaining_sick_leave"],
            "annual_leave_count": request["remaining_annual_leave"], 
            "casual_leave_count": request["remaining_casual_leave"],  
        }
        leave_requests.append(requested_leave_data)
    return leave_requests

def get_user_leave_status(current_user):
    if current_user.get('user_type') not in ["HR", "Manager", "Employee"]:
        raise HTTPException(status_code=403, detail="Unauthorized, only Employees can view leave status")
    try:
        cursor = collection_add_leave_request.find(
            {"user_email": current_user.get('user_email')},
            {"leaveType": 1, "startDate": 1, "dayCount": 1, "submitdate": 1,"submitdatetime": 1, "status": 1, "_id": 0}
        ).sort("submitdatetime", -1)  # Sort by submitdate in descending order
        results = list(cursor)
        if not results:
            raise HTTPException(status_code=404, detail="No leave found for the given employee")
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_hr_leave_service(current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view bills")
    excluded_statuses = ["approved", "rejected"]
    leaves_hr = []
    for leave in collection_add_leave_request.find({"status": {"$nin": excluded_statuses}}):
        leaves_data = {
            "leaveRequestId": leave["leave_id"],
            "leaveType": leave["leaveType"],
            "user_email": leave["user_email"],
            "dayCount": leave["dayCount"],
            "status": leave["status"]
        }
        leaves_hr.append(leaves_data)
    return leaves_hr

def update_hr_leave_status(leave_id, status_data, current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can update bills")
    existing_leave = collection_add_leave_request.find_one({"leave_id": leave_id})
    if not existing_leave:
        raise HTTPException(status_code=404, detail="leave not found")
    collection_add_leave_request.update_one({"leave_id": leave_id}, {"$set": {"status": status_data.new_status}})
    return {"message": f"leave {leave_id} updated successfully"}


def create_manager_leave_count(request_data,current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view bills")

    if current_user:
        test_request_data = {
            "sickLeaveCount":request_data.sickLeaveCount,
            "casualLeaveCount":request_data.casualLeaveCount,
            "annualLeaveCount":request_data.annualLeaveCount,
            "submitdate": request_data.submitdate,
            "user_Email":current_user.get("user_email"),
            "type":"Employee",
        }
        collection_add_manager_leave_count.insert_one(test_request_data)
        return {"message": "Test request created successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found")


def get_manager_leave_count(current_user_details):
    if current_user_details.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view bills")
    manager_leave_count = []
    for count in collection_add_manager_leave_count.find():
        manager_count_data = {
            "sickLeaveCount": count["sickLeaveCount"],
            "annualLeaveCount": count["annualLeaveCount"],
            "casualLeaveCount": count["casualLeaveCount"],
            "submitdate": count["submitdate"],
            "user_Email":current_user_details.get("user_email"),            
            "user_type": "Manager"
        }
        manager_leave_count.append(manager_count_data)
    return manager_leave_count


def create_employee_leave_count(request_data,current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view bills")

    if current_user:
        test2_request_data = {
            "sickLeaveCount":request_data.sickLeaveCount,
            "casualLeaveCount":request_data.casualLeaveCount,
            "annualLeaveCount":request_data.annualLeaveCount,
            "submitdate": request_data.submitdate,
            "user_Email":current_user.get("user_email"),
            "type":"Employee",
        }
        collection_add_employee_leave_count.insert_one(test2_request_data)
        return {"message": "Test request created successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found")


def get_employee_leave_count(current_user_details):
    if current_user_details.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view bills")
    employee_leave_count = []
    for count in collection_add_employee_leave_count.find():
        employee_count_data = {
            "sickLeaveCount": count["sickLeaveCount"],
            "annualLeaveCount": count["annualLeaveCount"],
            "casualLeaveCount": count["casualLeaveCount"],
            "submitdate": count["submitdate"],
            "user_Email":current_user_details.get("user_email"),            
            "user_type": "Employee"
        }
        employee_leave_count.append(employee_count_data)
    return employee_leave_count


def get_user_leave_report(email=None):
    leave_reports = []
    filter_query = {}  # Initialize an empty filter query

    if email:
        filter_query["user_email"] = email  # Filter by user_email if email is provided

    for request in collection_add_leave_request.find(filter_query):
        leave_report_data = {
            "leave_id": request["leave_id"],
            "user_type": request["user_type"],
            "user_name": request["user_name"],
            "user_email": request["user_email"],
            "leaveType": request["leaveType"],
            "startDate": request["startDate"],
            "dayCount": request["dayCount"],
            "submitdate": request["submitdate"],
            "status": request["status"],  # Keep the original status
        }
        leave_reports.append(leave_report_data)

    return leave_reports

def generate_pdf(leave_reports):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    elements = []

    # Title
    elements.append(Paragraph("Leave Report", styles['Title']))

    # Table Data
    data = []
    table_header = [
        "Leave ID",
        "User Name",
        "User Email",
        "Leave Type",
        "Start Date",
        "Day Count",
        "Submit Date",
        "Status",
    ]
    data.append(table_header)

    for report in leave_reports:
        row = [
            report['leave_id'],
            report['user_name'],
            report['user_email'],
            report['leaveType'],
            report['startDate'],
            str(report['dayCount']),
            report['submitdate'],
            report['status'],
        ]
        data.append(row)

    # Create Table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    return buffer

def create_new_leave(request_data, current_user):
    existing_leave= collection_leaves.find_one({
        "user_email":request_data.user_email,
        "start_date":request_data.start_date,
        "end_date":request_data.end_date
    })
    if existing_leave:
         raise HTTPException(status_code=400, detail="Leave already applied")
    try:
        last_leave = collection_leaves.find_one(sort=[("_id", -1)])
        last_id = last_leave["leave_id"] if last_leave else "B000"
        last_seq = int(last_id[1:])
        new_seq = last_seq + 1
        leave_id = f"L{new_seq:03d}"
        data = {
            "leave_id": leave_id,
            "user_type": current_user.get('user_type'),
            "user_email": current_user.get("user_email"),
            "user_email":request_data.user_email,
            "name": request_data.name,
            "start_date": request_data.start_date,
            "end_date": request_data.end_date,
            "leave_type": request_data.leave_type,
            "status": "pending"
        }

        result= collection_leaves.insert_one(data)
        return {"message": "Leave Inserted successfully", "leave_id": leave_id}
      
    except Exception as e:
        print(f"Error: {e}")  # Debugging print statement
        {"message": f"An error occurred while inserting the leave: {str(e)}"}

def get_leave_service(current_user):
    current_email=current_user.get("user_email")
    excluded_statuses = ["approved", "rejected"]
    leaves=[]
    try:
        for leave in collection_leaves.find({"status": {"$nin": excluded_statuses}}):
            leave_data={
                "leave_id": leave.get("leave_id",""),
                "name": leave.get("name", ""),
                "emp_id": leave.get("emp_id", ""),
                "start_date": leave.get("start_date", ""),
                "end_date": leave.get("end_date", ""),
                "leave_type": leave.get("leave_type", ""),
                "leave_status": leave.get("leave_status", "Pending")
            }
            leaves.append(leave_data)
        if not leaves:  
            raise HTTPException(status_code=404, detail="Employee leave data not found")    
            
        else:
            return leaves
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
    
def get_remaining_leaves_service(current_user):
    email = current_user.get("user_email")
    remaining_leaves = collection_remaining_leaves.find_one({"user_email": email})

    try:
        if remaining_leaves:
            # Ensure all necessary keys exist in the document
            if all(key in remaining_leaves for key in ["total_sick_leave", "sick_leave_taken", "total_vacation_leave", "vacation_leave_taken", "total_personal_leave", "personal_leave_taken"]):
                # Calculate remaining leaves
                remaining_sick_leave = remaining_leaves["total_sick_leave"] - remaining_leaves["sick_leave_taken"]
                remaining_vacation_leave = remaining_leaves["total_vacation_leave"] - remaining_leaves["vacation_leave_taken"]
                remaining_personal_leave = remaining_leaves["total_personal_leave"] - remaining_leaves["personal_leave_taken"]

                # Update remaining leaves in the database
                collection_leaves.update_one(
                    {"user_email": email},
                    {
                        "$set": {
                            "sick_leave_remaining": remaining_sick_leave,
                            "vacation_leave_remaining": remaining_vacation_leave,
                            "personal_leave_remaining": remaining_personal_leave
                        }
                    }
                )

                return {
                    "sick_leave_remaining": remaining_sick_leave,
                    "vacation_leave_remaining": remaining_vacation_leave,
                    "personal_leave_remaining": remaining_personal_leave
                }
            else:
                raise HTTPException(status_code=500, detail="Leave data is incomplete")
        else:
            # Return default values if data not found
            return {
                "sick_leave_remaining": 0,
                "vacation_leave_remaining": 0,
                "personal_leave_remaining": 0
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    
def get_ot_data_employees(current_user):
    if current_user.get("user_type") in ["HR"]:
        try:
            ot_chart_data_list_emp=[]
            for ot_data in collection_working_hours.find():
                email=ot_data.get("u_email")
                totOT=ot_data.get("totalOT")
                fixedOT=ot_data.get("fixedOT")
                ot_chart_data={
                    "name":" ",
                    "role":" ",
                    "completed":totOT,
                    "remaining":fixedOT-totOT
                }

                user_data = collection_user.find_one({"user_email": email})
                if user_data and user_data.get("user_type")=="Employee":
                    ot_chart_data["name"] = user_data.get("name", " ")
                    ot_chart_data["role"] = user_data.get("user_role", " ")
                    ot_chart_data_list_emp.append(ot_chart_data)
            return(ot_chart_data_list_emp)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    else:
        raise HTTPException(status_code=403, detail="User is not authorized to view this data.")


def get_ot_data_manager(current_user):
    if current_user.get("user_type") in ["HR"]:
        try:
            ot_chart_data_list_man=[]
            for ot_data in collection_working_hours.find():
                email=ot_data.get("u_email")
                totOT=ot_data.get("totalOT")
                fixedOT=ot_data.get("fixedOT")
                ot_chart_data={
                    "name":" ",
                    "role":" ",
                    "completed":totOT,
                    "remaining":fixedOT-totOT
                }

                user_data = collection_user.find_one({"user_email": email})
                if user_data and user_data.get("user_type")=="Manager":
                    ot_chart_data["name"] = user_data.get("name", " ")
                    ot_chart_data["role"] = user_data.get("user_role", " ")
                    ot_chart_data_list_man.append(ot_chart_data)
            return(ot_chart_data_list_man)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    else:
        raise HTTPException(status_code=403, detail="User is not authorized to view this data.")
    



def parse_cv_and_store(c_id,fs):
    try:
        candidate=collection_new_candidate.find_one({"c_id":c_id})
        v_id=candidate.get("vacancy_id")
        cv_id=candidate.get("cv")
        vacancy=collection_add_vacancy.find_one({"vacancy_id":v_id})
        jd=vacancy.get("job_description")

        status,matching_score=process_resume(cv_id,fs,jd)

        if status != "Success":
            return {"error": status}
        collection_new_candidate.update_one({"c_id": c_id}, {"$set": {"score": float(matching_score)}})
        return "Success", matching_score
        
    except FileNotFoundError:
        return f"File not found: {cv_id}", None
    except PyPDF2.errors.PdfReadError:
        return f"Error reading PDF: {cv_id}", None
    except Exception as e:
        return f"An error occurred while processing {cv_id}: {e}", None
    

def add_interview_service(interview_data,current_user):
    if current_user.get("user_type")=="HR":
        try:
            last_interview = collection_interviews.find_one(sort=[("_id", -1)])
            last_id = last_interview["i_id"] if last_interview else "I000"
            last_seq = int(last_id[1:])
            new_seq = last_seq + 1
            i_id = f"I{new_seq:03d}"
            data={
                "i_id":i_id,
                "c_id":interview_data.c_id,
                "date":interview_data.date,
                "time":interview_data.time,
                "venue":interview_data.venue,
                "interviewer_id":interview_data.interviewer_id,
                "confirmed_date":interview_data.confirmed_date,
                "result":"pending"
            }
            collection_interviews.insert_one(data)
            return {"message": "Interview created successfully"}
        except Exception as e:
            print(f"Error: {e}")  
            {"message": f"An error occurred while inserting the leave: {str(e)}"}

def update_candidate_response(c_id):
    update_result=collection_interviews.update_one({"c_id":c_id},{"$set": {"result": "confirmed"}})
    if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Interview not found")
    else:
        return{"message":"Interview status updated successfully"}
    
def get_interviews_service(current_user):
    if current_user.get('user_type') != "HR":
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can view candidates")
    excluded_statuses = ["approved"]
    interviews = []
    for interview in collection_interviews.find({"status": {"$nin": excluded_statuses}}).sort("score",-1):
        interview_data = {
            "i_id": interview["i_id"],
            "c_id": interview["c_id"],
            "date": interview["date"],
            "time": interview["time"],
            "venue":interview["venue"],
            "interviewer_id": interview["interviewer_id"],
            "confirmed_date":interview["confirmed_date"],
            "result":interview["result"]  
    
        }
        interviews.append(interview_data)
    return interviews

async def download_candidate_cv_interview(cv_id, fs,current_user):
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
    
async def fetch_interviewer_email_details(c_id: str, current_user, base_url: str):
    interview = collection_interviews.find_one({"c_id": c_id})
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    email = interview.get("interviewer_id")
    interviewer = collection_user.find_one({"user_email": email})
    if interviewer is None:
        raise HTTPException(status_code=404, detail="Interviewer not found")
    
    find_cv=collection_new_candidate.find_one({"c_id":c_id})
    if find_cv is None:
        raise HTTPException(status_code=404, detail="Candidate CV not found")
    
    cv_id=find_cv.get("cv")
   
    details = {
        "email": email,
        "name": interviewer.get("user_name"),
        "date": interview.get("date"),
        "time": interview.get("time"),
        "venue": interview.get("venue"),
        "cv": f"{base_url}/download_cv/{cv_id}"
    }

    return details


### Create Temp Vacancy for Testing ###
async def create_temp_job_vacancies_service(job_title: str, job_type: str, work_mode: str, file) -> JSONResponse:
    try:
        # Generate vacancy_id
        last_vacancy = collection_job_vacancies.find_one(sort=[("_id", -1)])
        last_id = last_vacancy["vacancy_id"] if last_vacancy else "V000"
        last_seq = int(last_id[1:])
        new_seq = last_seq + 1
        vacancy_id = f"V{new_seq:03d}"
        
        # Upload file to GridFS
        file_id = grid_fs.put(file.file, filename=file.filename, content_type=file.content_type)
        
        # Save metadata in MongoDB
        job_vacancy = JobVacancy(
            vacancy_id=vacancy_id,
            job_title=job_title,
            job_type=job_type,
            work_mode=work_mode,
            pdf_id=str(file_id),  # Store the file_id
        )
        collection_job_vacancies.insert_one(job_vacancy.dict())
        
        return JSONResponse(
            content={"message": "Job vacancy created successfully", "job_vacancy": job_vacancy.dict()},
            status_code=200
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to create job vacancy. Please try again.")


### Get job Requirments ###
async def get_file_service(file_id: str) -> StreamingResponse:
    try:
        file = grid_fs.get(ObjectId(file_id))
        return StreamingResponse(file, media_type=file.content_type, headers={"Content-Disposition": f"attachment; filename={file.filename}"})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail="File not found.")


### Get vacancy details ###
async def get_all_job_vacancies_service() -> list:
    try:
        job_vacancies = collection_job_vacancies.find()
        vacancies_list = []
        for job_vacancy in job_vacancies:
            vacancies_list.append({
                "job_title": job_vacancy["job_title"],
                "work_mode": job_vacancy["work_mode"],
                "job_type": job_vacancy["job_type"],
                "pdf_id": job_vacancy["pdf_id"],
                "vacancy_id": job_vacancy["vacancy_id"]
            })
        return vacancies_list
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to retrieve job vacancies details")
        

    
#### Candidate Upload CV #####
async def create_candidate_cv_service(vacancy_id: str, name: str, email: str, contact_number: str, cv) -> JSONResponse:
    try:
        # Generate c_id
        last_cv = collection_job_applications.find_one(sort=[("_id", -1)])
        last_id = last_cv["c_id"] if last_cv else "C000"
        last_seq = int(last_id[1:])
        new_seq = last_seq + 1
        c_id = f"C{new_seq:03d}"

        # Fetch job details based on vacancy_id
        job_details = collection_add_vacancy.find_one({"vacancy_id": vacancy_id})
        if not job_details:
            raise HTTPException(status_code=404, detail="Vacancy ID not found")

        # Upload CV to GridFS
        cv_id = grid_fs.put(cv.file, filename=cv.filename, content_type=cv.content_type)

        # Save application details in MongoDB
        job_application = JobApplicatons(
            c_id=c_id,
            name=name,
            email=email,
            contact_number=contact_number,
            cv=str(cv_id),  # Store the CV file's ObjectId
            job_title=job_details.get("possition"),
            job_type=job_details.get("job_type"),
            work_mode=job_details.get("work_mode"),
        )
        collection_job_applications.insert_one(job_application.dict())

        return JSONResponse(content={"message": "Job application created successfully", "job_application": job_application.dict()},
                            status_code=200)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to create job application. Please try again.")
    
def download_vacancy_pdf(pdf_file_id, fs):
    try:
        # Retrieve the file from GridFS
        file = fs.get(ObjectId(pdf_file_id))
        if file is None:
            raise HTTPException(status_code=404, detail="pdf not found")
        # Return the file content as a StreamingResponse with the original filename
        return StreamingResponse(file, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={file.filename}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_all_vacancies_service() -> list:
    try:
        vacancies = collection_add_vacancy.find()
        vacancies_list = []
        for vacancy in vacancies:
            vacancies_list.append({
                "vacancy_id": vacancy["vacancy_id"],
                "job_type": vacancy["job_type"],
                "possition": vacancy["possition"],
                "work_mode": vacancy["work_mode"],
                "pdf_file_id": str(vacancy["pdf_file_id"]) if "pdf_file_id" in vacancy else None
            })
        return vacancies_list
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to retrieve vacancies details")

