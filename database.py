from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')

database = client.HCM

collection_user_login = database["users"]