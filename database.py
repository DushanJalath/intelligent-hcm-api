# database.py
from pymongo import MongoClient
from gridfs import GridFS

client = MongoClient('mongodb://localhost:27017')

database = client.HCM

collection_user = database["user"] 
collection_user_login = database["users"]
collection_add_vacancy =database["AddVacancy"]
collection_leave_predictions = database["LeavePredictions"]
collection_bills = database["bills"]
collection_new_candidate = database["new_candidates"]

collection_candidate_pdf = database["candidate_pdf"]

fs = GridFS(database,collection="candidate_pdfs")