from fastapi import FastAPI

app = FastAPI(title="Pearls AQI Predictor API")

@app.get("/")
def read_root():
    return {"message": "Welcome to Pearls AQI Predictor"}
