import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use environment variable if set, otherwise default to local Postgres (user 'apple' on mac)
DATABASE_URL = os.getenv(
  "DATABASE_URL", 
  "postgresql+psycopg2://postgres:Awais123@my-todo-app.c3so26oscjij.ap-southeast-2.rds.amazonaws.com:5432/my-todo-app")

# Create engine and session factory
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
