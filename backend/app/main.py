"""FastAPI app: creates the app and includes the route modules."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config, db
from app.memory import Memory
from app.routes import companies, tenders


def create_app(conn=None, mem=None, storage_dir: Path | None = None) -> FastAPI:
    """Tests pass their own conn/mem/storage; otherwise they are opened at startup."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.conn is None:
            if not os.environ.get("GROQ_API_KEY"):
                raise RuntimeError("Missing setting: GROQ_API_KEY")
            storage = config.storage_dir()
            app.state.storage_dir = storage
            app.state.conn = db.connect(str(storage / "tendersathi.db"))
            app.state.mem = Memory(str(storage / "chroma"))
        db.reset_stuck_runs(app.state.conn)
        if app.state.mem is not None:
            app.state.mem.warm_up()
        yield

    app = FastAPI(title="TenderSathi", lifespan=lifespan)
    app.state.conn, app.state.mem, app.state.storage_dir = conn, mem, storage_dir
    app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins(),
                       allow_methods=["*"], allow_headers=["*"])
    app.include_router(companies.router)
    app.include_router(tenders.router)
    return app


app = create_app()
