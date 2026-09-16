"""预应力钢束伸长量 MVP 的 FastAPI 应用入口。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.calculation import router as calculation_router


app = FastAPI(title="Tendon MVP", version="0.1.0")

# MVP 阶段允许本地 Vite 开发服务器调用后端接口。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calculation_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """返回后端健康状态。"""
    return {"status": "ok"}
