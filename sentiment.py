import os
import requests
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from azure.storage.blob import BlobServiceClient
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

router = APIRouter()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "indexblob8482"  
FAISS_FOLDER = "faiss_index"
FAISS_INDEX_BLOB = "index.faiss"
PKL_INDEX_BLOB = "index.pkl"

#For graph data
GRAPH_CONTAINER_NAME = "graph-sentiment"
GRAPH_BLOB_NAME = "entity_sentiment_tree.html"
GRAPH_FILE_PATH = "entity_sentiment_tree.html"

# Azure OpenAI Config
AZURE_OPENAI_DEPLOYMENT = "gpt-4o-mini"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = "https://gen-sentiment.openai.azure.com/"
AZURE_OPENAI_API_VERSION = "2024-08-01-preview"

vectordb = None  

# Function to download the FAISS index and load it
def download_faiss_from_blob():
    global vectordb
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)

    os.makedirs(FAISS_FOLDER, exist_ok=True)

    with open(os.path.join(FAISS_FOLDER, FAISS_INDEX_BLOB), "wb") as f:
        f.write(container_client.get_blob_client(FAISS_INDEX_BLOB).download_blob().readall())

    with open(os.path.join(FAISS_FOLDER, PKL_INDEX_BLOB), "wb") as f:
        f.write(container_client.get_blob_client(PKL_INDEX_BLOB).download_blob().readall())

    print("FAISS files downloaded and stored locally.")

    embeddings_model = HuggingFaceEmbeddings(model_name="BAAI/bge-large-en-v1.5", model_kwargs={'device': 'cpu', "trust_remote_code": True})
    vectordb = FAISS.load_local(FAISS_FOLDER, embeddings=embeddings_model, allow_dangerous_deserialization=True)

    print("FAISS index loaded successfully!")

#load graph to backend
def fetch_html_from_blob():
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=GRAPH_CONTAINER_NAME, blob=GRAPH_BLOB_NAME)

    html_content = blob_client.download_blob().readall().decode("utf-8")
    with open(GRAPH_FILE_PATH, "w", encoding="utf-8") as file:
        file.write(html_content)

    print("Graph updated")


fetch_html_from_blob()
download_faiss_from_blob()

llm = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    openai_api_key=AZURE_OPENAI_API_KEY,
    deployment_name=AZURE_OPENAI_DEPLOYMENT,
    openai_api_version=AZURE_OPENAI_API_VERSION,
)

prompt = PromptTemplate(
    input_variables=["context", "query"],
    template="""Context: {context}\nQuestion: {query} | 
    You are an AI financial sentiment analyst with expertise in understanding and interpreting market news.
    Your role is to provide deep and clear insights on finance, stock trends, and market events.
    If a query is unrelated to finance, stock markets, or economics, politely refuse to answer. However, you can reply to the greetings."""
)

question_feeder = RunnablePassthrough()

rag_chain = {
    "context": vectordb.as_retriever(),
    "query": question_feeder
} | prompt | llm

def execute_chain(chain, question):
    answer = chain.invoke(question)
    return answer

@router.get("/chat/{message}")
async def chat(message: str):
    try:
        answer = execute_chain(rag_chain, message)
        return {"response": answer.content.strip()}
    except Exception as e:
        return {"error": str(e)}

@router.post("/reload-faiss")
async def reload_faiss():
    """Manually reloads the FAISS index from Azure Blob Storage."""
    try:
        download_faiss_from_blob()
        return {"message": "FAISS index successfully reloaded."}
    except Exception as e:
        return {"error": str(e)}
    
@router.get("/get-graph")
async def get_graph():
    try:
        with open(GRAPH_FILE_PATH, "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="Graph not available yet.", status_code=404)
