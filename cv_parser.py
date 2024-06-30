import PyPDF2
import spacy
import re
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from bson import ObjectId
from pymongo import MongoClient
from gridfs import GridFS
from database import collection_job_vacancies,collection_job_applications

def process_resume(cv_text,jd_text):
    # Connect to MongoDB
    #client = MongoClient('mongodb://localhost:27017/')
    #db = client['mydatabase']
    #fs = GridFS(db)

    """try:
        # Retrieve the CV from GridFS
        cv_file = grid_fs.get(ObjectId(cv_id))
        cv_text = ""
        pdf_reader = PyPDF2.PdfReader(cv_file)
        for page in pdf_reader.pages:
            cv_text += page.extract_text()
    except FileNotFoundError:
        return f"File not found: {cv_id}", None
    except PyPDF2.errors.PdfReadError:
        return f"Error reading PDF: {cv_id}", None
    except Exception as e:  
        return f"An error occurred while processing {cv_id}: {e}", None
    
    try:
        # Retrieve the JD from GridFS
        jd_file = grid_fs.get(ObjectId(jd_id))
        jd_text = ""
        pdf_reader = PyPDF2.PdfReader(jd_file)
        for page in pdf_reader.pages:
            jd_text += page.extract_text()
    except FileNotFoundError:
        return f"File not found: {jd_id}", None
    except PyPDF2.errors.PdfReadError:
        return f"Error reading PDF: {jd_id}", None
    except Exception as e:  
        return f"An error occurred while processing {cv_id}: {e}", None
    
"""
    nlp1 = spacy.load(r"cv_parser_output\model-best")

    doc = nlp1(cv_text)
    parsed_data = [(ent.label_, ent.text) for ent in doc.ents]

    skills = [item[1] for item in parsed_data if item[0] == 'Skills']
    experience = [item[1] for item in parsed_data if item[0] == 'Experience']
    education = [item[1] for item in parsed_data if item[0] == 'Education']
    degree= [item[1] for item in parsed_data if item[0] == 'Degree']
    


    skills_text = ' '.join(skills)
    experience_text = ' '.join(experience)
    education_text=' '.join(education)
    degree_text=' '.join(degree)
    resume_text = skills_text + ' ' + experience_text+ ' ' + education_text+' '+degree_text
    resume_text_cleaned = re.sub(r'\s+', ' ', resume_text)
    resume_text_cleaned = re.split(r'•|\n|, ', resume_text_cleaned)
    resume_data_text = ' '.join(resume_text_cleaned)

    nlp = spacy.load("en_core_web_sm")

    job_doc = nlp(jd_text)
    resume_doc = nlp(resume_data_text)

    job_text = " ".join([sent.text for sent in job_doc.sents])
    resume_text = " ".join([sent.text for sent in resume_doc.sents])

    vectorizer = CountVectorizer()
    vectorizer.fit_transform([job_text, resume_text])
    job_vector = vectorizer.transform([job_text])
    resume_vector = vectorizer.transform([resume_text])

    cosine_sim = cosine_similarity(job_vector, resume_vector)[0][0]
    matching_score = round(cosine_sim, 2) * 100

    return "Success", matching_score

