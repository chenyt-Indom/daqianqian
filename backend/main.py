"""到签签 API 主入口"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import init_db
from routes import auth, team, checkin, debug, mailbox

app = FastAPI(title="到签签 API", version="2.0.0")

@app.on_event("startup")
def startup(): init_db(); print("✅ 到签签 API 已启动")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(team.router)
app.include_router(checkin.router)
app.include_router(debug.router)
app.include_router(mailbox.router)

@app.get("/api/health")
def health(): return {"status": "ok", "app": "到签签", "version": "2.0.0"}

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
    @app.get("/")
    async def serve_frontend(): return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8765)
