
import pdfplumber
import spacy
import re
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Function to extract text from PDF using pdfplumber
'''def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ''
        for page in pdf.pages:
            text += page.extract_text()
    return text'''

# Function to preprocess text
def preprocess_text(text):
    text = re.sub(r'\s+', ' ', text)  # Clean text
    return text.strip()

# Function to load and parse CV using custom spaCy model
def parse_cv(cv_text, nlp_model):
    doc = nlp_model(cv_text)
    parsed_data = [(ent.label_, ent.text) for ent in doc.ents]
    return parsed_data

# Function to calculate cosine similarity between two vectors
def calculate_cosine_similarity(vector1, vector2):
    return cosine_similarity(vector1.reshape(1, -1), vector2.reshape(1, -1))[0][0] * 100

# Main function to process CV and job description
'''parsing_model=spacy.load("/content/drive/MyDrive/CV_Parser/cv_parsing_model")
sen_model=SentenceTransformer('bert-base-nli-mean-tokens')'''
def process_resume_and_job(cv_text, jd_text,parsing_model,sen_model):
    # Step 1: Extract text from PDFs
    '''cv_text = extract_text_from_pdf(cv_path)
    jd_text = extract_text_from_pdf(jd_path)'''
    
    # Step 2: Preprocess text
    cv_text = preprocess_text(cv_text)
    jd_text = preprocess_text(jd_text)
    
    # Step 3: Load custom spaCy model for CV parsing
    nlp_cv = parsing_model
    
    # Step 4: Parse CV using custom spaCy model
    parsed_cv_data = parse_cv(cv_text, nlp_cv)
    parsed_cv_text = ' '.join([text for _, text in parsed_cv_data]) if parsed_cv_data else ''

    
    # Step 5: Generate embeddings using Gensim Doc2Vec
    documents = [TaggedDocument(parsed_cv_text.split(), [0]), TaggedDocument(jd_text.split(), [1])]
    model = Doc2Vec(documents, vector_size=100, window=5, min_count=1, workers=4)
    cv_vector = model.dv[0]
    jd_vector = model.dv[1]
    
    # Step 6: Generate embeddings using Sentence Transformers
    sentence_model = sen_model
    cv_embeddings = sentence_model.encode([parsed_cv_text])
    jd_embeddings = sentence_model.encode([jd_text])
    
    # Step 7: Calculate cosine similarity scores
    gensim_cosine_sim = calculate_cosine_similarity(cv_vector, jd_vector)
    sentence_transformers_cosine_sim = calculate_cosine_similarity(cv_embeddings, jd_embeddings)
    
    # Step 8: Final matching score
    matching_score = (gensim_cosine_sim + sentence_transformers_cosine_sim) / 2
   
    
    return matching_score