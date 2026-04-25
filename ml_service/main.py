from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import numpy as np
import pandas as pd
import pickle
import os
import contextlib

# Global variables
products_list = []
similarity_matrix = None
products_df = None

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global products_list, similarity_matrix, products_df
    print("[OK] Starting up ML Service...")
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    try:
        # Load the precomputed similarity matrix
        with open(os.path.join(BASE_DIR, "similarity.pkl"), "rb") as f:
            similarity_matrix = pickle.load(f)
        
        # Load the products dataframe
        with open(os.path.join(BASE_DIR, "product_list.pkl"), "rb") as f:
            products_df = pickle.load(f)
            
        print(f"[OK] Loaded {len(products_df)} products | Similarity matrix shape: {getattr(similarity_matrix, 'shape', 'N/A')}")
        
        # Build products_list for easy frontend consumption
        for _, row in products_df.iterrows():
            products_list.append({
                "product_id": str(row["product_id"]),
                "title": str(row["title"]),
                "image_path": ""  # No image paths in the new dataset
            })
            
    except Exception as e:
        print(f"[ERROR] Failed to load model files: {e}")
        
    yield
    print("Shutting down")

app = FastAPI(title="Image Recommender API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Schemas ──────────────────────────────────────────────────────────────────
class ProductOut(BaseModel):
    product_id: str
    title: str
    image_path: str

class RecommendRequest(BaseModel):
    product_id: str
    top_n: int = 5

class RecommendResponse(BaseModel):
    query_id: str
    query_title: str
    recommendations: List[ProductOut]

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Welcome to the Recommender API (NLP Similarity Model)."}

@app.get("/products", response_model=List[ProductOut])
def get_products(limit: int = Query(5000, ge=1)):
    """Return a list of available products."""
    if not products_list:
        raise HTTPException(status_code=503, detail="Dataset not loaded.")
    return products_list[:limit]

@app.get("/search", response_model=List[ProductOut])
def search_products(q: str = Query(..., min_length=1), limit: int = 10):
    """Simple text search on product titles."""
    if not products_list:
        raise HTTPException(status_code=503, detail="Dataset not loaded.")
        
    q_lower = q.lower()
    results = [p for p in products_list if q_lower in p["title"].lower()]
    return results[:limit]

@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    """Return top-N semantically similar items using precomputed similarity matrix."""
    if similarity_matrix is None or products_df is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded — similarity.pkl / product_list.pkl missing.",
        )

    # Find the index of the requested product_id in the dataframe
    idx = None
    for i, p in enumerate(products_list):
        if p["product_id"].lower() == req.product_id.strip().lower():
            idx = i
            break

    if idx is None:
        raise HTTPException(
            status_code=404,
            detail=f"Product '{req.product_id}' not found in dataset. Use /search to find valid IDs."
        )

    # Get precomputed similarity scores for this product
    scores = similarity_matrix[idx]
    
    # Sort and pick top_n (excluding the queried item itself)
    top_indices = np.argsort(scores)[::-1]
    top_indices = [int(i) for i in top_indices if i != idx][: req.top_n]

    recs = [
        ProductOut(
            product_id=products_list[i]["product_id"],
            title=products_list[i]["title"],
            image_path=products_list[i]["image_path"],
        )
        for i in top_indices
    ]

    return RecommendResponse(
        query_id=products_list[idx]["product_id"],
        query_title=products_list[idx]["title"],
        recommendations=recs,
    )
