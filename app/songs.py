from fastapi import APIRouter, HTTPException, Query
import httpx
import voyager
import numpy as np
import json
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from fastapi import Depends
import logging
import colorlog

router = APIRouter()

# Initialize the voyager index (once)
vector_dimension = 3  # Number of dimensions in your vector
index = voyager.Index(space=voyager.Space.Euclidean, num_dimensions=vector_dimension)

# Create a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set format for the logger
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white'
    }
)

# Create a console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)

# Add handler to the logger
logger.addHandler(ch)

# Dummy function to create embeddings, replace with your own function
def create_embedding(song_data):
    return np.random.rand(vector_dimension)

@router.get("/create_embeddings")
async def get_songs(limit: int = 10):
    url = f"http://core.curator.atemkeng.eu/api/song/clean?limit={limit}"
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
        logger.error(f"Failed to fetch songs: HTTP {response.status_code}")

async def fetch_and_preprocess_data(limit: int = 6000):
    logger.info("Starting to fetch and preprocess data")

    url = f"http://core.curator.atemkeng.eu/api/song/clean?limit={limit}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        logger.error(f"Failed to fetch songs: HTTP {response.status_code}")
        logger.error(f"Response: {response.text}")
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch songs")

    logger.info("Data fetched successfully")
    data = response.json()

    # Convert to DataFrame
    df = pd.DataFrame(data)
    logger.info("Data converted to DataFrame")

    # Log a snippet of the DataFrame
    logger.info(f"DataFrame head or Snipped of Entire data (Just the first 5): \n{df.head()}")

    # Identify and handle non-numeric columns
    non_numeric_columns = df.select_dtypes(include=['object']).columns
    if len(non_numeric_columns) > 0:
        logger.warn(f"Non-numeric columns found: {non_numeric_columns}")
        # TODO: Handle non-numeric data here (convert, remove, etc.)
        # For example: df = df.drop(columns=non_numeric_columns)

    # Apply scaling to numeric data only
    numeric_df = df.select_dtypes(include=[np.number])
    scaler = StandardScaler()
    df_scaled = scaler.fit_transform(numeric_df)
    logger.info("Numeric data scaling complete")

    # Add to Voyager index
    for i, row in enumerate(df_scaled):
        index.add_item(np.array(row, dtype=np.float32), i)
        logger.debug(f"Item {i} added to Voyager index")

    logger.info("Data preprocessing and addition to index complete")

# Add these routes
@router.get("/initialize")
async def initialize_index():
    logger.info("Starting to fetch and preprocess data")
    await fetch_and_preprocess_data()
    return {"status": "Index initialized"}

@router.get("/search/{song_id}")
async def search_similar_songs(song_id: int, k: int = 5):
    logger.info(f"Searching for similar songs to song_id {song_id}")
    logger.debug(f"k: {k}")
    try:
        # Fetch the vector for the given song_id
        vector = index.get_vector(song_id)
        logger.info(f"Vector for song_id {song_id} fetched successfully")
        logger.debug(f"Vector: {vector}")

        # Search for similar songs
        neighbors, distances = index.query(vector, k)

        # Convert to JSON-serializable types
        neighbors_list = neighbors.tolist() if hasattr(neighbors, 'tolist') else list(neighbors)
        distances_list = distances.tolist() if hasattr(distances, 'tolist') else list(distances)

        return {"similar_songs": neighbors_list, "distances": distances_list}
    except Exception as e:
        # Call the function to initialize index
        return {"error": str(e)}
        logger.error(f"Failed to fetch vector for song_id {song_id}: {e}")
