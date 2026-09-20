"""预应力钢束伸长量 MVP 的 FastAPI 应用入口。"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.calculation import router as calculation_router
from app.api.batch import router as batch_router
from app.api.dxf_import import router as dxf_import_router


app = FastAPI(title="Tendon MVP", version="0.1.0")

# 使用逗号分隔的环境变量配置已部署前端域名；本地开发保留 Vite 默认地址。
cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(calculation_router)
app.include_router(batch_router)
app.include_router(dxf_import_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """返回后端健康状态。"""
    return {"status": "ok"}
