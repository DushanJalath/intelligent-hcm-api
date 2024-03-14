from model import User,W_Hours,Bills,Leaves,Vacancy,Candidate,Parsed_Candidates,Interview
import motor.motor_asyncio

client=motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')

database=client.HCM

colection_user=database.user
collection_work_hours=database.w_hours
collection_bills=database.bills
collection_leaves=database.leaves
collection_vacancy=database.vacancy
collection_candidate=database.candidate
collection_parsed_candidate=database.parsed_candidates
collection_interview=database.interview
