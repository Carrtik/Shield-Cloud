from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Self Healing Service", version="1.0.0")

@app.get("/health/live")
def liveness_probe():
    return {"status": "alive"}

@app.get("/health/ready")
def readiness_probe():
    return {"status": "ready"}

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=3006, reload=True)
