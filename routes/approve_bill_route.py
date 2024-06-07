from models import StatusUpdate
from fastapi import FastAPI, UploadFile, File,Response,APIRouter,HTTPException
from fastapi import HTTPException,Depends
from database import collection_user, collection_bills
from utils import get_current_user
from models import User_login,User
from fastapi.security import OAuth2PasswordBearer
from bson import ObjectId

router = APIRouter()

@router.get("/hrapprovebilllist/")
async def get_bills_for_hr(current_user: User = Depends(get_current_user)):
    if current_user.get('user_type') not in ["HR"]:
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can approve bills")
    
    cursor = collection_bills.find(
    {"status": "pending"},
    {"category": 1, "submitdate": 1, "_id": 1}
    )

    results = list(cursor)

    if not results:
        raise HTTPException(status_code=404, detail="No bills found for approval")

    documents = [{**document, "_id": str(document["_id"])} for document in results]

    return documents


@router.put("/updateStatus/{row_id}")
async def update_status(row_id: str,status_update: StatusUpdate,current_user: User = Depends(get_current_user)):
    if current_user.get('user_type') not in ["HR"]:
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can approve bills")
    
    bill_object_id = ObjectId(row_id)
    print(status_update.new_status)
    
    result = collection_bills.update_one({"_id": bill_object_id}, {"$set": {"status": status_update.new_status}})
    return {"message": status_update.new_status}
    
 

@router.get("/get_pdf/{row_id}")
async def get_pdf(row_id: str,current_user: User = Depends(get_current_user)):
    if current_user.get('user_type') not in ["HR"]:
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can approve bills")
    
    object_id = ObjectId(row_id)
        
    document = collection_bills.find_one({'_id': object_id})
    pdf_data = document['pdf_content']
    print("hii")
    return Response(content=pdf_data, media_type='application/pdf')