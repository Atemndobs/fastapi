from fastapi import APIRouter, HTTPException, Query
import httpx
import voyager
import numpy as np
import json
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from fastapi import Depends

router = APIRouter()

# Initialize the voyager index (once)
vector_dimension = 5  # Number of dimensions in your vector
index = voyager.Index(space=voyager.Space.Euclidean, num_dimensions=vector_dimension)

# Dummy function to create embeddings, replace with your own function
def create_embedding(song_data):
    return np.random.rand(vector_dimension)

@router.get("/create_embeddings")
async def get_songs(limit: int = 10):
    url = f"http://nginx/api/song/clean?limit={limit}"
    print(url)
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code == 200:
        songs = response.json()
        for song in songs:
            embedding = create_embedding(song)
            index.add_item(np.array(embedding))
        return {"message": "Embeddings created and added to index"}
    else:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch songs")


# Fetch and preprocess songs data
async def fetch_and_preprocess_data(limit: int = 6000):
    url = f"http://nginx/api/song/clean?limit={limit}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch songs")

    data = response.json()

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Standardize the data11
    scaler = StandardScaler()
    df_scaled = scaler.fit_transform(df)

    # Add to Voyager index
    for i, row in enumerate(df_scaled):
        index.add_item(np.array(row, dtype=np.float32), i)


# Add these routes
@router.get("/initialize")
async def initialize_index():
    await fetch_and_preprocess_data()
    return {"status": "Index initialized"}

@router.get("/search/{song_id}")
async def search_similar_songs(song_id: int, k: int = 5):
    try:
        # Fetch the vector for the given song_id
        vector = index.get_vector(song_id)

        # Search for similar songs
        neighbors, distances = index.query(vector, k)

        # Convert to JSON-serializable types
        neighbors_list = neighbors.tolist() if hasattr(neighbors, 'tolist') else list(neighbors)
        distances_list = distances.tolist() if hasattr(distances, 'tolist') else list(distances)

        return {"similar_songs": neighbors_list, "distances": distances_list}
    except Exception as e:
       #call the function to initialize index
         return {"error": str(e)}
  
         
