from fastapi import FastAPI
from app.routers import leaderboard
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Arcade Leaderboard Backend", version="0.2.0")
app.add_middleware(CORSMiddleware,
    allow_origins=['https://html-classic.itch.zone'],
    allow_methods=['*'], allow_headers=['*'])

app.include_router(leaderboard.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
