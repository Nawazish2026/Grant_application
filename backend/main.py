from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.database import init_db
from backend.routers import assessments, analysis

init_db()

app = FastAPI(
    title="Grant Application Completeness Assistant",
    description=(
        "An AI-powered tool that reviews draft funding applications "
        "against supplied grant guidelines. Advisory use only."
    ),
    version="1.0.0",
)

app.include_router(assessments.router)
app.include_router(analysis.router)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")
app.mount("/assets", StaticFiles(directory=str(frontend_dir / "assets")), name="assets")


@app.get("/")
async def serve_frontend():
    return FileResponse(str(frontend_dir / "index.html"))


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Grant Application Completeness Assistant"}
