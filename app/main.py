import logging

from fastapi import FastAPI

from app.database import init_db
from app.routers import images, posts, review

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="AI Image Matching Engine",
    description="Matches blog posts to the right images, with a mismatch guard that refuses bad pairings.",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(images.router)
app.include_router(posts.router)
app.include_router(review.router)
