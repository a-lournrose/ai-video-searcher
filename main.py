from __future__ import annotations

from fastapi import FastAPI
import uvicorn

from app.presentation.http.snapshot import router as snapshot_router
from app.presentation.http.search_router import router as search_router


app = FastAPI()
app.include_router(search_router)
app.include_router(snapshot_router)


if __name__ == "__main__":
    # Для reload нужно указывать строку "main:app",
    # иначе uvicorn не сможет отслеживать изменения в файлах
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )