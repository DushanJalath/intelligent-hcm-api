import PyPDF2
import spacy
import re
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from bson import ObjectId
from pymongo import MongoClient
from gridfs import GridFS

def process_resume(cv_id, fs,job_description_json):
    # Connect to MongoDB
    #client = MongoClient('mongodb://localhost:27017/')
    #db = client['mydatabase']
    #fs = GridFS(db)

    try:
        # Retrieve the CV from GridFS
        cv_file = fs.get(ObjectId(cv_id))
        text = ""
        pdf_reader = PyPDF2.PdfReader(cv_file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    except FileNotFoundError:
        return f"File not found: {cv_id}", None
    except PyPDF2.errors.PdfReadError:
        return f"Error reading PDF: {cv_id}", None
    except Exception as e:  
        return f"An error occurred while processing {cv_id}: {e}", None

    nlp1 = spacy.load(r"cv_parser_output\model-best")

    doc = nlp1(text)
    parsed_data = [(ent.label_, ent.text) for ent in doc.ents]

    skills = [item[1] for item in parsed_data if item[0] == 'Skills']
    experience = [item[1] for item in parsed_data if item[0] == 'Experience']
    education = [item[1] for item in parsed_data if item[0] == 'Education']
    


    skills_text = ' '.join(skills)
    experience_text = ' '.join(experience)
    education_text=' '.join(education)
    resume_text = skills_text + ' ' + experience_text+ ' ' + education_text
    resume_text_cleaned = re.sub(r'\s+', ' ', resume_text)
    resume_text_cleaned = re.split(r'•|\n|, ', resume_text_cleaned)
    resume_data_text = ' '.join(resume_text_cleaned)

    nlp = spacy.load("en_core_web_sm")

    job_description_text = ''
    if job_description_json:
        job_description_text = ' '.join([value for key, value in job_description_json.items()])
    job_doc = nlp(job_description_text)
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
