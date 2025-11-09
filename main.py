import os
import logging
from datetime import datetime
import asyncio
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import boto3
import models, schemas
from database import SessionLocal, engine, Base

# ---------------- Logging Setup ----------------
LOG_FILE = "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ---------------- Database Setup ----------------
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Todo App")

# Allow cross-origin for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths for templates and static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- AWS S3 Setup ----------------
BUCKET_NAME = "todoappkis3"  # replace with your bucket name
s3_client = boto3.client("s3")  # relies on EC2 IAM Role
UPLOAD_INTERVAL = 10  # seconds

async def auto_upload_logs():
    """Background task to upload logs to S3 every 10 seconds."""
    while True:
        if os.path.exists(LOG_FILE):
            s3_key = f"logs/app_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
            try:
                s3_client.upload_file(LOG_FILE, BUCKET_NAME, s3_key)
                logger.info(f"Uploaded log file to s3://{BUCKET_NAME}/{s3_key}")
            except Exception as e:
                logger.error(f"Failed to upload log file: {e}")
        await asyncio.sleep(UPLOAD_INTERVAL)

@app.on_event("startup")
async def startup_event():
    """Start background log uploader when app starts."""
    asyncio.create_task(auto_upload_logs())
    logger.info("Started background log uploader task.")

# ---------------- Frontend Route ----------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    logger.info("Home page accessed")
    return templates.TemplateResponse("index.html", {"request": request})

# ---------------- API Routes (CRUD) ----------------
@app.get("/api/todos/", response_model=list[schemas.TodoResponse])
def read_todos(db: Session = Depends(get_db)):
    todos = db.query(models.Todo).order_by(models.Todo.id).all()
    logger.info(f"Retrieved {len(todos)} todos")
    return todos

@app.post("/api/todos/", response_model=schemas.TodoResponse)
def create_todo(todo: schemas.TodoCreate, db: Session = Depends(get_db)):
    db_todo = models.Todo(title=todo.title, completed=todo.completed)
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    logger.info(f"Created Todo: {db_todo.title} (ID: {db_todo.id})")
    return db_todo

@app.put("/api/todos/{todo_id}", response_model=schemas.TodoResponse)
def update_todo(todo_id: int, todo: schemas.TodoUpdate, db: Session = Depends(get_db)):
    db_todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    if not db_todo:
        logger.warning(f"Todo ID {todo_id} not found for update")
        raise HTTPException(status_code=404, detail="Todo not found")
    db_todo.title = todo.title
    db_todo.completed = todo.completed
    db.commit()
    db.refresh(db_todo)
    logger.info(f"Updated Todo ID {todo_id}")
    return db_todo

@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    db_todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    if not db_todo:
        logger.warning(f"Todo ID {todo_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Todo not found")
    db.delete(db_todo)
    db.commit()
    logger.info(f"Deleted Todo ID {todo_id}")
    return {"message": "Todo deleted"}
