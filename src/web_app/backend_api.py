import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

app = FastAPI(title="Pearls AQI Predictor API")

# Setup CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint to serve predictions
@app.get("/api/predictions")
def get_predictions():
    # The predictions are saved to docs/predictions.json by the GitHub Action
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    predictions_file = os.path.join(base_dir, "docs", "predictions.json")
    
    if not os.path.exists(predictions_file):
        raise HTTPException(status_code=404, detail="Predictions not found. Please run the prediction pipeline.")
        
    try:
        with open(predictions_file, "r") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files (the frontend) at the root
# Note: we mount it last so the API route is caught first
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
docs_dir = os.path.join(base_dir, "docs")
if os.path.exists(docs_dir):
    app.mount("/", StaticFiles(directory=docs_dir, html=True), name="static")
