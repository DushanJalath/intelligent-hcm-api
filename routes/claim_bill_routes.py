from reportlab.pdfgen import canvas 
from reportlab.pdfbase.ttfonts import TTFont 
from reportlab.pdfbase import pdfmetrics 
from reportlab.lib import colors 
from reportlab.lib.pagesizes import letter
from mindee import Client, PredictResponse, product
from fastapi import FastAPI, UploadFile, File,Response,APIRouter,HTTPException
from fastapi import HTTPException,Depends
import io
from database import collection_user, collection_bills
from models import User_login,User
from utils import get_current_user
from fastapi.security import OAuth2PasswordBearer
from models import Bills
import os

router = APIRouter()
mindee_client = Client(api_key="61297519804e6cd73b887e036394d9d5")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/upload/")
async def uploadimage(image: UploadFile = File(...),current_user: User = Depends(get_current_user)):
    if current_user.get('user_type') not in ["HR", "Manager" ,"Employee"]:
        raise HTTPException(status_code=403, detail="Unauthorized, only Employees can upload bills")
    try:
            if image is None:
                return {"error": "No image provided"}

            with open("invoiceimage.jpg", "wb") as temp_file:
                temp_file.write(await image.read())

            input_doc = mindee_client.source_from_path("invoiceimage.jpg")

            result: PredictResponse = mindee_client.parse(product.InvoiceV4, input_doc)

            return {"storename": result.document.inference.prediction.supplier_name.value,
                    "invoicenumber": result.document.inference.prediction.invoice_number.value,
                    "date": result.document.inference.prediction.date.value,
                    "totalamount": result.document.inference.prediction.total_amount.value

            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    
@router.post("/confirminvoice/")
async def uploadimage(data:Bills,current_user: User = Depends(get_current_user)):
    if current_user.get('user_type') not in ["HR", "Manager" ,"Employee"]:
        raise HTTPException(status_code=403, detail="Unauthorized, only Employees can upload bills")
    try:
        buffer = io.BytesIO()
        data = data.dict()
        data['u_id'] =current_user.get('user_id')
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "Invoice Details")
        c.drawString(100, 700, f"UserID: {data['u_id']}")
        c.drawString(100, 670, f"Category: {data['category']}")
        c.drawString(100, 640, f"Store Name: {data['storename']}")
        c.drawString(100, 610, f"Amount: {data['amount']}")
        c.drawString(100, 580, f"Date: {data['Date']}")
        c.drawString(100, 550, f"Invoice Number: {data['bill_id']}")
        image_path = 'invoiceimage.jpg' 
        c.drawImage(image_path, 150, 100, width=300, height=300)
        c.save()
        
        #Get the PDF content as bytes
        pdf_content = buffer.getvalue()
        
        data['pdf_content'] = pdf_content
       
        collection_bills.insert_one(data)
        print("Data and PDF stored in MongoDB successfully")
        os.remove(image_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
      

@router.get("/billstatus/")
async def get_bills_for_employee(current_user: User = Depends(get_current_user)):
    if current_user.get('user_type') not in ["HR", "Manager" ,"Employee"]:
        raise HTTPException(status_code=403, detail="Unauthorized, only Employees can upload bills")
    try:
        cursor = collection_bills.find(
        {"u_id": current_user.get('user_id')},
        {"category": 1, "submitdate": 1, "status": 1, "_id": 0}
        )
    
        results = list(cursor)
    
        if not results:
            raise HTTPException(status_code=404, detail="No bills found for the given employee ID")
    
        return results
        

          
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
