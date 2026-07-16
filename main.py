import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------- 資料庫設定 ----------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")

# Render 給的是 postgresql://,psycopg3 需要 postgresql+psycopg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ---------- 資料表 ----------
class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100), nullable=False)
    year = Column(Integer, nullable=True)


# ---------- Pydantic 模型 ----------
class BookIn(BaseModel):
    title: str
    author: str
    year: int | None = None


class BookOut(BookIn):
    id: int

    model_config = {"from_attributes": True}


# ---------- App ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # 啟動時自動建表
    yield


app = FastAPI(title="Book CRUD API", lifespan=lifespan)


@app.get("/")
def hello():
    return {"message": "Hello"}


# ---------- CRUD ----------
@app.post("/books", response_model=BookOut, status_code=201)
def create_book(payload: BookIn):
    with SessionLocal() as db:
        book = Book(**payload.model_dump())
        db.add(book)
        db.commit()
        db.refresh(book)
        return book


@app.get("/books", response_model=list[BookOut])
def list_books():
    with SessionLocal() as db:
        return db.query(Book).order_by(Book.id).all()


@app.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int):
    with SessionLocal() as db:
        book = db.get(Book, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book


@app.put("/books/{book_id}", response_model=BookOut)
def update_book(book_id: int, payload: BookIn):
    with SessionLocal() as db:
        book = db.get(Book, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        for k, v in payload.model_dump().items():
            setattr(book, k, v)
        db.commit()
        db.refresh(book)
        return book


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with SessionLocal() as db:
        book = db.get(Book, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        db.delete(book)
        db.commit()
