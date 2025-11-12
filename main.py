# ------------------------------------ this part makes a file and then push that log file to s3 ------------------------------------

# import os
# import logging
# from datetime import datetime
# import asyncio
# from fastapi import FastAPI, Request, Depends, HTTPException
# from fastapi.responses import HTMLResponse
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
# from fastapi.middleware.cors import CORSMiddleware
# from sqlalchemy.orm import Session
# import boto3
# import models, schemas
# from database import SessionLocal, engine, Base

# # ---------------- Logging Setup ----------------
# LOG_FILE = "app.log"

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[
#         logging.FileHandler(LOG_FILE),
#         logging.StreamHandler()
#     ]
# )

# logger = logging.getLogger(__name__)

# # ---------------- Database Setup ----------------
# Base.metadata.create_all(bind=engine)

# app = FastAPI(title="Todo App")

# # Allow cross-origin for local dev
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # restrict in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Paths for templates and static files
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
# app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# # Dependency to get DB session
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # ---------------- AWS S3 Setup ----------------
# BUCKET_NAME = "meritodoapps3"  # replace with your bucket name
# s3_client = boto3.client("s3")  # relies on EC2 IAM Role
# UPLOAD_INTERVAL = 10  # seconds

# async def auto_upload_logs():
#     """Background task to upload logs to S3 every 10 seconds."""
#     while True:
#         if os.path.exists(LOG_FILE):
#             s3_key = f"logs/app_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
#             try:
#                 s3_client.upload_file(LOG_FILE, BUCKET_NAME, s3_key)
#                 logger.info(f"Uploaded log file to s3://{BUCKET_NAME}/{s3_key}")
#             except Exception as e:
#                 logger.error(f"Failed to upload log file: {e}")
#         await asyncio.sleep(UPLOAD_INTERVAL)

# @app.on_event("startup")
# async def startup_event():
#     """Start background log uploader when app starts."""
#     asyncio.create_task(auto_upload_logs())
#     logger.info("Started background log uploader task.")

# # ---------------- Frontend Route ----------------
# @app.get("/", response_class=HTMLResponse)
# def home(request: Request):
#     logger.info("Home page accessed")
#     return templates.TemplateResponse("index.html", {"request": request})

# # ---------------- API Routes (CRUD) ----------------
# @app.get("/api/todos/", response_model=list[schemas.TodoResponse])
# def read_todos(db: Session = Depends(get_db)):
#     todos = db.query(models.Todo).order_by(models.Todo.id).all()
#     logger.info(f"Retrieved {len(todos)} todos")
#     return todos

# @app.post("/api/todos/", response_model=schemas.TodoResponse)
# def create_todo(todo: schemas.TodoCreate, db: Session = Depends(get_db)):
#     db_todo = models.Todo(title=todo.title, completed=todo.completed)
#     db.add(db_todo)
#     db.commit()
#     db.refresh(db_todo)
#     logger.info(f"Created Todo: {db_todo.title} (ID: {db_todo.id})")
#     return db_todo

# @app.put("/api/todos/{todo_id}", response_model=schemas.TodoResponse)
# def update_todo(todo_id: int, todo: schemas.TodoUpdate, db: Session = Depends(get_db)):
#     db_todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
#     if not db_todo:
#         logger.warning(f"Todo ID {todo_id} not found for update")
#         raise HTTPException(status_code=404, detail="Todo not found")
#     db_todo.title = todo.title
#     db_todo.completed = todo.completed
#     db.commit()
#     db.refresh(db_todo)
#     logger.info(f"Updated Todo ID {todo_id}")
#     return db_todo

# @app.delete("/api/todos/{todo_id}")
# def delete_todo(todo_id: int, db: Session = Depends(get_db)):
#     db_todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
#     if not db_todo:
#         logger.warning(f"Todo ID {todo_id} not found for deletion")
#         raise HTTPException(status_code=404, detail="Todo not found")
#     db.delete(db_todo)
#     db.commit()
#     logger.info(f"Deleted Todo ID {todo_id}")
#     return {"message": "Todo deleted"}


# ------------------------------------ now the logs will not occupy local space anymore ------------------------------------


import os
import logging
import boto3
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas
from database import SessionLocal, engine, Base

# ---------------- AWS S3 Setup ----------------
BUCKET_NAME = "meritodoapps3"  # your S3 bucket name
s3_client = boto3.client("s3")  # uses EC2 IAM Role or environment credentials


# ---------------- Custom Logging Handler ----------------
class S3LogHandler(logging.Handler):
    def __init__(self, bucket_name: str, s3_client, upload_every: int = 5):
        super().__init__()
        self.bucket_name = bucket_name
        self.s3_client = s3_client
        self.log_buffer = []
        self.upload_every = upload_every  # upload after N logs
        self.log_file_key = (
            f"logs/app_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        )

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_buffer.append(msg + "\n")
            # Upload after every N logs
            if len(self.log_buffer) >= self.upload_every:
                self.flush_to_s3()
        except Exception:
            self.handleError(record)

    def flush_to_s3(self):
        if not self.log_buffer:
            return
        log_data = "".join(self.log_buffer)
        try:
            # Append mode simulation: get existing data and re-upload
            try:
                existing_obj = self.s3_client.get_object(
                    Bucket=self.bucket_name, Key=self.log_file_key
                )
                existing_data = existing_obj["Body"].read().decode("utf-8")
            except self.s3_client.exceptions.NoSuchKey:
                existing_data = ""

            new_data = existing_data + log_data
            self.s3_client.put_object(
                Body=new_data.encode("utf-8"),
                Bucket=self.bucket_name,
                Key=self.log_file_key,
            )
            self.log_buffer.clear()
        except Exception as e:
            print(f"Failed to push logs to S3: {e}")


# ---------------- Logging Setup ----------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Formatter for all log messages
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Add S3 Handler
s3_handler = S3LogHandler(BUCKET_NAME, s3_client)
s3_handler.setFormatter(formatter)

# Add console handler too (optional)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger.addHandler(s3_handler)
logger.addHandler(console_handler)

# ---------------- Database Setup ----------------
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Todo App")

# Allow cross-origin for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths for templates and static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount(
    "/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"
)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- Routes ----------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    logger.info("Home page accessed")
    return templates.TemplateResponse("index.html", {"request": request})


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
