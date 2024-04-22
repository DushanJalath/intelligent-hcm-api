from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')

database = client.HCM

collection_user = database["user"] 
collection_user_login = database["users"]
collection_add_vacancy =database["AddVacancy"]