import uvicorn
from fastapi import FastAPI
from threading import Thread

app = FastAPI()

@app.get("/ping")
async def health_probe():
    return {"message": "pong"}

def start_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

def start_background_server():
    thread = Thread(target=start_server)
    thread.daemon = True
    thread.start()
