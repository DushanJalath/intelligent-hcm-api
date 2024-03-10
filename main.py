from fastapi import FastAPI
from chatbot import create_llm_connection,create_embedding_model,creare_vector_db,build_conversation


app=FastAPI()
chat_llm=create_llm_connection()
llm_embeddings=create_embedding_model()
vector_db=creare_vector_db(llm_embeddings)
conversational_chain=build_conversation(vector_db,chat_llm)

@app.get("/chat_request/{input}")
def chatRequest(input:str):
    return conversational_chain.run(input)