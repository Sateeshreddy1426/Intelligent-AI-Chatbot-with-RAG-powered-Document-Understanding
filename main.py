import os
import json
import requests
import chromadb
import fitz  # PyMuPDF for PDF processing
import openai
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="docs")

# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Flask API
app = Flask(__name__)

# Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "".join([page.get_text() for page in doc])
    return text

# Function to embed and store documents
def add_document(doc_id, text):
    embedding = embedding_model.encode([text])[0].tolist()
    collection.add(ids=[doc_id], embeddings=[embedding], documents=[text])

# RAG response generation
def generate_response(user_query):
    query_embedding = embedding_model.encode([user_query])[0].tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=3)
    retrieved_docs = "\n".join(results["documents"][0]) if results["documents"] else ""
    prompt = f"User query: {user_query}\nRelevant context: {retrieved_docs}\nAI Response:"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are an intelligent chatbot."},
                  {"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

# Kore.ai Webhook Endpoint
@app.route("/koreai-webhook", methods=["POST"])
def koreai_webhook():
    data = request.json
    user_query = data.get("query", "")
    response_text = generate_response(user_query)
    return jsonify({"response": response_text})

# Run Flask App
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
