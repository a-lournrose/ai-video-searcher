from __future__ import annotations

import os

from fastapi import FastAPI
import uvicorn

from app.presentation.http.snapshot import router as snapshot_router
from app.presentation.http.search_router import router as search_router

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8001"))


app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # разрешить все домены
    allow_credentials=True,
    allow_methods=["*"],          # разрешить любые методы
    allow_headers=["*"],          # разрешить любые заголовки
)

app.include_router(search_router)
app.include_router(snapshot_router)


if __name__ == "__main__":
    # Для reload нужно указывать строку "main:app",
    # иначе uvicorn не сможет отслеживать изменения в файлах
    uvicorn.run(
        "main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=True,
    )