from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

#                                user:password
DATABASE_URL = "postgresql://postgres:postgres@172.30.12.229:5432/gambledata"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()