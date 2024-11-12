from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Any, TypeVar
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as gc_firestore

# Initialize Firebase app
cred = credentials.Certificate('../python_script/firebase_credentials.json')
firebase_admin.initialize_app(cred)

# Get Firestore client
db = firestore.client()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

T = TypeVar('T')

def convert_to_json_serializable(data: Any) -> Any:
    """Convert Firestore data types to JSON serializable formats"""
    if data is None:
        return None
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, (firestore.DocumentReference, firestore.DocumentSnapshot)):
        return str(data.path)
    elif isinstance(data, gc_firestore.GeoPoint):
        return {'latitude': data.latitude, 'longitude': data.longitude}
    elif isinstance(data, dict):
        return {k: convert_to_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_json_serializable(i) for i in data]
    elif hasattr(data, 'get'):  # Handle DocumentSnapshot
        return convert_to_json_serializable(data.to_dict())
    return data

class Points(BaseModel):
    generalPoints: int = 0
    postPoints: int = 0
    reviewPoints: int = 0

class UserBase(BaseModel):
    email: str
    firstName: str
    lastName: str
    username: str
    uid: str
    points: Points = Field(default_factory=Points)
    playlists: List[str] = Field(default_factory=list)
    emailVerified: bool = False

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    createdAt: str

class PlaylistBase(BaseModel):
    name: str
    description: Optional[str] = ""
    restaurants: List[str] = Field(default_factory=list)
    color: str = "#f97316"
    author: str
    username: str

class PlaylistCreate(PlaylistBase):
    pass

class PlaylistRead(PlaylistBase):
    id: str
    createdAt: str

def validate_and_serialize(data):
    try:
        serialized = convert_to_json_serializable(data)
        # Verify serialization
        json.dumps(serialized)
        return serialized
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data serialization error: {str(e)}"
        )

# --- User Endpoints ---
@app.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    try:
        # Check UID uniqueness
        uid_query = db.collection("users").where("uid", "==", user.uid).get()
        if len(list(uid_query)) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this authentication already exists"
            )

        # Check username availability
        user_doc = db.collection("users").document(user.username).get()
        if user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken"
            )

        # Prepare user data
        user_data = {
            **jsonable_encoder(user),
            "createdAt": datetime.utcnow().isoformat(),
            "points": {
                "generalPoints": 0,
                "postPoints": 0,
                "reviewPoints": 0
            },
            "playlists": []
        }

        # Create user document
        db.collection("users").document(user.username).set(user_data)
        
        return {
            "message": "User created successfully",
            "username": user.username
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error creating user: {str(e)}")  # For debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/users/{username}", response_model=UserRead)
async def get_user(username: str):
    try:
        user_doc = db.collection("users").document(username).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        # Convert document data to dict and make it JSON-serializable
        user_data = user_doc.to_dict()
        serialized_data = convert_to_json_serializable(user_data)
        
        return serialized_data

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error getting user: {str(e)}")  # For debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/users/auth/{uid}", response_model=UserRead)
async def get_user_by_uid(uid: str):
    try:
        users = db.collection("users").where("uid", "==", uid).limit(1).get()
        user_list = list(users)
        
        if not user_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with UID '{uid}' not found"
            )

        # Convert document data to dict and make it JSON-serializable
        user_data = user_list[0].to_dict()
        serialized_data = convert_to_json_serializable(user_data)
        
        return serialized_data

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error getting user by UID: {str(e)}")  # For debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# --- Playlist Endpoints ---
@app.post("/users/{username}/playlists", status_code=status.HTTP_201_CREATED)
async def create_playlist(username: str, playlist: PlaylistCreate):
    try:
        # Verify user exists
        user_doc = db.collection("users").document(username).get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        # Verify ownership
        if playlist.username != username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create playlist for another user"
            )

        # Create playlist with auto ID
        playlist_ref = db.collection("users").document(username).collection("playlists").document()
        
        playlist_data = {
            **playlist.dict(),
            "id": playlist_ref.id,
            "createdAt": datetime.utcnow().isoformat()
        }

        # Save playlist
        playlist_ref.set(playlist_data)

        # Update user's playlists array
        db.collection("users").document(username).update({
            "playlists": firestore.ArrayUnion([playlist_ref.id])
        })

        return {
            "message": "Playlist created successfully",
            "id": playlist_ref.id
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/users/{username}/playlists", response_model=List[PlaylistRead])
async def get_user_playlists(username: str):
    try:
        user_doc = db.collection("users").document(username).get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        playlists = db.collection("users").document(username).collection("playlists").get()
        return [validate_and_serialize(doc.to_dict()) for doc in playlists]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/users/{username}/playlists/{playlist_id}", response_model=PlaylistRead)
async def get_playlist(username: str, playlist_id: str):
    try:
        doc = db.collection("users").document(username).collection("playlists").document(playlist_id).get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )
        return validate_and_serialize(doc.to_dict())
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.put("/users/{username}/playlists/{playlist_id}")
async def update_playlist(username: str, playlist_id: str, playlist: PlaylistCreate):
    try:
        playlist_ref = db.collection("users").document(username).collection("playlists").document(playlist_id)
        if not playlist_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )

        # Update playlist
        playlist_ref.update(playlist.dict())
        return {"message": "Playlist updated successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.delete("/users/{username}/playlists/{playlist_id}")
async def delete_playlist(username: str, playlist_id: str):
    try:
        # Get refs
        user_ref = db.collection("users").document(username)
        playlist_ref = user_ref.collection("playlists").document(playlist_id)

        # Verify playlist exists
        if not playlist_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )

        # Delete playlist
        playlist_ref.delete()

        # Update user's playlists array
        user_ref.update({
            "playlists": firestore.ArrayRemove([playlist_id])
        })

        return {"message": "Playlist deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Extra endpoints as needed...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)