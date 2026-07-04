import os
import logging
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine, DB_TYPE, ensure_assessment_attempt_columns, ensure_assessment_attempt_events_table, ensure_assessment_cascade_constraints, ensure_assessment_columns, ensure_classroom_columns, ensure_codespace_columns, ensure_material_attachment_columns, ensure_password_reset_table, ensure_unit_columns, ensure_user_profile_columns
from seed import seed_database
from routes import activity_routes, assessment_routes, auth_routes, classroom_routes, codespace_routes, coding_routes, notification_routes, template_routes, unit_routes, material_routes, test_routes, result_routes, user_routes

load_dotenv()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log database initialization
    print(f"Initializing {DB_TYPE} database...")
    
    Base.metadata.create_all(bind=engine)
    ensure_user_profile_columns()
    ensure_password_reset_table()
    ensure_assessment_columns()
    ensure_assessment_attempt_columns()
    ensure_assessment_attempt_events_table()
    ensure_assessment_cascade_constraints()
    ensure_unit_columns()
    ensure_classroom_columns()
    ensure_codespace_columns()
    ensure_material_attachment_columns()
    seed_database()
    
    print(f"Database ready ({DB_TYPE})")
    yield
    print("Shutting down...")


app = FastAPI(title="ClassNest API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def log_slow_requests(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    if duration_ms > 1000:
        logger.warning("slow_endpoint method=%s path=%s duration_ms=%s", request.method, request.url.path, duration_ms)
    return response

# Configure CORS from environment
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://class-nest-phi.vercel.app/")
allow_origins = [
    FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://class-nest-phi.vercel.app/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in [auth_routes.router, user_routes.router, classroom_routes.router, unit_routes.router, material_routes.router, assessment_routes.router, coding_routes.router, codespace_routes.router, activity_routes.router, notification_routes.router, template_routes.router, test_routes.router, result_routes.router]:
    app.include_router(router, prefix="/api")


@app.get("/api/health")
def health(): return {"status": "ok"}
