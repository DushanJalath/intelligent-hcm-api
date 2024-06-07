# products_routes.py
from fastapi import FastAPI,APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.security import OAuth2PasswordBearer
import joblib
from datetime import datetime, timedelta
from database import collection_leave_predictions , collection_user,fs,collection_candidate_pdf,collection_new_candidate
from models import PredictionRequest,User
from utils import create_future_data , get_current_user,is_holiday
from gridfs import GridFS
from bson import ObjectId
from fastapi.responses import JSONResponse, StreamingResponse

router = APIRouter()

# Define your OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/predict/")
async def predict_attendance(request: PredictionRequest , current_user: User = Depends(get_current_user)):
    if current_user.get('user_type') not in ["HR", "Manager"]:
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can predict attendance")
    try:       
        # Load the machine learning model
        rf_model = joblib.load("random_forest_regression_model3_month.joblib")

        # Predict attendance for the given date
        future_data = create_future_data(request.date)
        predicted_attendance = rf_model.predict(future_data)
        predicted_attendance_rounded = int(round(predicted_attendance[0]))  # Round to nearest integer
        # Store prediction in MongoDB
        collection_leave_predictions.insert_one({"date": request.date, "predicted_attendance": predicted_attendance_rounded})

        return {"predicted_attendance": predicted_attendance_rounded}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/predict/chart/")
async def predict_attendance_chart(request: PredictionRequest , current_user: User = Depends(get_current_user)):
    if current_user.get('user_type') not in ["HR", "Manager"]:
        raise HTTPException(status_code=403, detail="Unauthorized, only HR can approve vacancies")
    try:
        # Load the machine learning model
        rf_model = joblib.load("random_forest_regression_model3_month.joblib")

        # Convert the input date to a datetime object
        input_date = datetime.strptime(request.date, '%m%d')

        # Create data for the next 7 days
        prediction_data = []
        for i in range(1, 8):
            next_date = (input_date + timedelta(days=i)).strftime('%m%d')
            future_data = create_future_data(next_date)
            predicted_attendance = rf_model.predict(future_data)
            predicted_attendance_rounded = int(round(predicted_attendance[0]))  # Round to nearest integer
            prediction_data.append({"date": next_date, "predicted_attendance": predicted_attendance_rounded})

        return prediction_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/upload_cv/{c_id}")
async def upload_cv(c_id: str, file: UploadFile = File(...)):
    try:
        # Save the uploaded file to GridFS
        cv_id = fs.put(file.file, filename=file.filename)

        # Update the candidate document in the database with the new cv_id
        collection_new_candidate.update_one({"c_id": c_id}, {"$set": {"cv": str(cv_id)}})

        return {"cv_id": str(cv_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_gridfs():
    return fs

@router.get("/download_cv/{cv_id}")
async def download_cv(cv_id: str, fs: GridFS = Depends(get_gridfs), current_user: User = Depends(get_current_user)):
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