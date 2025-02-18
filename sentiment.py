import os
import requests
from fastapi import APIRouter
from azure.storage.blob import BlobServiceClient
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "indexblob8482"  
FAISS_FOLDER = "faiss_index"
FAISS_INDEX_BLOB = "index.faiss"
PKL_INDEX_BLOB = "index.pkl"

# Azure OpenAI Config
AZURE_OPENAI_DEPLOYMENT = "gpt-4o-mini"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = "https://gen-sentiment.openai.azure.com/"
AZURE_OPENAI_API_VERSION = "2024-08-01-preview"

vectordb = None

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

    embeddings_model= HuggingFaceEmbeddings(model_name="BAAI/bge-large-en-v1.5", model_kwargs= {'device': 'cpu', "trust_remote_code": True})
    vectordb = FAISS.load_local(FAISS_FOLDER, embeddings=embeddings_model, allow_dangerous_deserialization=True)

    print("FAISS index loaded successfully!")

download_faiss_from_blob()

llm = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    openai_api_key=AZURE_OPENAI_API_KEY,
    deployment_name=AZURE_OPENAI_DEPLOYMENT,
    openai_api_version=AZURE_OPENAI_API_VERSION,
)

prompt = PromptTemplate(
    input_variables=["context", "query"],
    template="Context: {context}\nQuestion: {query} | Answer is short but meaningful way with justification"
)

@router.get("/chat/{message}")
async def chat(message: str):
    """Handles chat requests using FAISS for RAG + Azure OpenAI."""
    try:
        docs = vectordb.similarity_search(message, k=3)
        context = "\n\n".join(doc.page_content for doc in docs)

        formatted_prompt = prompt.format(
            context=context,
            query=message
        )

        response = llm.invoke(formatted_prompt)

        return {"response": response.content.strip()}

    except Exception as e:
        return {"error": str(e)}


@router.post("/reload-faiss")
async def reload_faiss():
    """Manually reloads FAISS index from Azure Blob Storage."""
    try:
        download_faiss_from_blob()
        return {"message": "FAISS index successfully reloaded."}
    except Exception as e:
        return {"error": str(e)}
