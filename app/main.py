from fastapi import FastAPI
from app.routers import leaderboard

app = FastAPI(title="Arcade Leaderboard Backend", version="0.2.0")

app.include_router(leaderboard.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
