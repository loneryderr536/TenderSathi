"""FastAPI app: creates the app and includes the route modules."""
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config, db
from app.memory import Memory
from app.routes import admin, auth, companies, gov, rfq, scout, tenders


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
        if config.scout_interval():
            threading.Thread(target=_scout_loop, args=(app,), daemon=True).start()
        yield

    app = FastAPI(title="TenderSathi", lifespan=lifespan)
    app.state.conn, app.state.mem, app.state.storage_dir = conn, mem, storage_dir
    app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins(),
                       allow_origin_regex=config.cors_origin_regex(), allow_methods=["*"], allow_headers=["*"])
    @app.get("/health", include_in_schema=False)
    def health():
        """For the host's health check (Railway)."""
        return {"ok": True}

    app.include_router(auth.router)
    app.include_router(companies.router)
    app.include_router(tenders.router)
    app.include_router(scout.router)
    app.include_router(gov.router)
    app.include_router(rfq.router)
    app.include_router(admin.router)
    return app


def _scout_loop(app: FastAPI):
    """Autonomous mode: sweep the portals every SCOUT_INTERVAL_SECONDS for the first business profile."""
    from app import graph

    while True:
        time.sleep(config.scout_interval())
        try:
            conn, mem = app.state.conn, app.state.mem
            companies = db.list_companies(conn)
            company_id = companies[0]["id"] if companies else None
            scout.sweep(conn, app.state.storage_dir, config.feed_path(), company_id,
                        lambda tid, run_id: graph.run_pipeline(conn, mem, tid, company_id, run_id=run_id))
        except Exception as e:   # a bad sweep must not kill the loop
            print(f"Scout sweep failed: {e}")


app = create_app()
