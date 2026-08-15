import logging

from fastapi import FastAPI

from app.api import tools, webhooks

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="reorder-line")
app.include_router(tools.router)
app.include_router(webhooks.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
