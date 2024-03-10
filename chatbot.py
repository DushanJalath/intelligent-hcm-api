import yaml,os
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import Chroma

def create_llm_connection():
    with open("cadentials.yaml") as f:
        cadentials=yaml.load(f,Loader=yaml.FullLoader)

    os.environ['OPENAI_API_KEY'] = cadentials['OPENAI_API_KEY']

    chat_llm=ChatOpenAI(
        openai_api_key=os.environ['OPENAI_API_KEY'],
        model='gpt-3.5-turbo',
        temperature=0.5,
        max_tokens=500
    )
    return chat_llm

def create_embedding_model():
    return HuggingFaceBgeEmbeddings(
                        model_name = 'BAAI/bge-small-en-v1.5',
                        model_kwargs = {'device' : 'cpu'},
                        encode_kwargs = {'normalize_embeddings': False}
    )

def creare_vector_db(llm_embeddings):
    loader=DirectoryLoader(
                    'data/',
                    loader_cls=PyPDFLoader,
                    glob='./*.pdf'
                )

    documents=loader.load() #load documents as pages

    text_splitter=RecursiveCharacterTextSplitter(
                            chunk_size=1000,
                            chunk_overlap=200 #get last 200 tokens to the next piece of chunk
                        )

    texts=text_splitter.split_documents(documents)

    if not os.path.exists("./db/00/"):
        print("Creating the DB")
        vector_db = Chroma.from_documents(
                                        documents = texts,
                                        embedding = llm_embeddings,
                                        persist_directory = 'db/00'
                                        )
    else:
        print("Loading the DB")
        vector_db = Chroma(
                        embedding_function = llm_embeddings,
                        persist_directory = 'db/00'
                        )   
    
    return vector_db



def  build_conversation(vector_db,chat_llm):
    memory=ConversationBufferMemory(
                            memory_key='chat_history',
                            return_messages=True
    )
    conversational_chain=ConversationalRetrievalChain.from_llm(
                                                        llm=chat_llm,
                                                        memory=memory,
                                                        retriever=vector_db.as_retriever()
    )
    return conversational_chain


def print_memory(conversational_chain):
    history=""
    memory_elements=conversational_chain.memory.chat_memory
    for idx,element in enumerate(memory_elements.messages):
        message=element.content
        if idx%2==0:
            history+=f"User :{message}\n"
        else:
            history+=f"Bot :{message}\n"
    return history