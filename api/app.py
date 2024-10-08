from fastapi import FastAPI
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.types import Document
from google.protobuf.timestamp_pb2 import Timestamp

# Initialize Firebase app (you need to replace 'firebase_credentials.json' with your actual service account key file)
cred = credentials.Certificate('../python_script/firebase_credentials.json')
firebase_admin.initialize_app(cred)

# Get a Firestore client
db = firestore.client()

app = FastAPI()

def convert_to_json_serializable(obj):
    if isinstance(obj, Document):
        return obj.to_dict()
    elif isinstance(obj, Timestamp):
        return obj.ToDatetime().isoformat()
    return obj


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/users")
async def get_users():
    docs = db.collection("users").stream()
    # Convert each document to a dictionary
    data = []
    for doc in docs:
        doc_dict = doc.to_dict()
        # Convert Firestore-specific types
        json_friendly_dict = {k: convert_to_json_serializable(v) for k, v in doc_dict.items()}
        data.append(json_friendly_dict)
    
    # Convert to JSON
    json_data = json.dumps(data, indent=2)
    print(json_data)
    return data
        # print(f"User ID: {doc.id}, Data: {doc.to_dict()}\n")
