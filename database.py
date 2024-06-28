# database.py
from pymongo import MongoClient
from gridfs import GridFS

client = MongoClient('mongodb+srv://oshen:oshen@cluster0.h2my8yk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')

database = client.HCM

collection_user = database["user"] 
collection_user_login = database["users"]
collection_add_vacancy =database["AddVacancy"]
collection_leave_predictions = database["LeavePredictions"]
collection_bills = database["bills"]
collection_bill_upload = database["BillUpload"] 
collection_new_candidate = database["new_candidates"]
collection_emp_vac_submit=database["empVacSubmit"]
collection_emp_time_rep=database["empTimeReport"]
collection_candidate_pdf = database["candidate_pdf"]

fs = GridFS(database,collection="candidate_pdfs")

fs_pic = GridFS(database, collection="user_profile_pic")