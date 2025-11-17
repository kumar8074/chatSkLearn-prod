# ===================================================================================
# Project: ChatSkLearn
# File: src/main.py
# Description: Fast API Application
# Author: LALAN KUMAR
# Created: [10-11-2025]
# Updated: [15-11-2025]
# LAST MODIFIED BY: LALAN KUMAR  [https://github.com/kumar8074]
# Version: 1.1.0
# ===================================================================================

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from src.routers.rag import router as rag_router

app = FastAPI(title="Scikit-learn Assistant")

# CORS middleware - Allow all origins for widget embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the absolute path to the frontend directory
current_dir = Path(__file__).parent
frontend_dir = current_dir / "frontend"

# Mount static files directory
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
else:
    print(f"Warning: Frontend directory not found at {frontend_dir}")

# Include API routers
app.include_router(rag_router)

# Root endpoint - serve index.html
@app.get("/")
async def read_root():
    """Serve the main frontend application"""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Frontend not found. Please ensure index.html exists in src/frontend/"}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sklearn-assistant",
        "frontend": "available" if (frontend_dir / "index.html").exists() else "not found"
    }

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",  
        host="0.0.0.0",
        port=8000,
        reload=True,  
        log_level="info",
        timeout_keep_alive=75,  
        loop="uvloop",
        limit_concurrency=1000,
        http="h11"  
    )