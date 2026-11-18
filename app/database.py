import os
from sqlmodel import Session,create_engine
from typing import Annotated #this bundles the type hint and the FastAPI dependency metadata together into a single variable (SessionDep)
from fastapi import Depends
from dotenv import load_dotenv
load_dotenv()
#DATABASE_URL = "sqlite:///cinema_wouri.db" ; Sql lite
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables")

#The below line initializes a SQLAlchemy Engine, which manages the core connection pool and communication dialect between your Python application and your database
#engine = create_engine(DATABASE_URL, echo=True) #echo=True. A debugging flag that configures SQLAlchemy to log every generated SQL statement—along with query parameters and transaction details—directly to your console (stdout)

# check_same_thread=False is required for SQLite in FastAPI
#connect_args = {"check_same_thread": False} #is required for SQLite to allow FastAPI to interact with the database across multiple threads
connect_args = {"prepare_threshold": None} # optinal in some cases
# pool_pre_ping=True prevents stale connection errors with cloud Postgres/Supabase
engine = create_engine(
    DATABASE_URL, 
    echo=True, 
    pool_pre_ping=True,
    connect_args=connect_args,
    pool_size=10,
    max_overflow=20
    )

""" def create_tables(): #Avoid SQLModel.metadata.create_all in Production  :: In production, replace SQLModel.metadata.create_all() with Alembic database migrations
    ""Create all tables defined by SQLModel Class""
    SQLModel.metadata.create_all(engine)   # metadata always check if the tables exists or not before proceeding to their creation

## get info about seeion pooling """

def get_session():
    """Unscoped session (connects as 'postgres' with BYPASSRLS for admin/public routes)."""
    with Session(engine) as session:
        yield session 
# Reusable dependency annotation for FastAPI routes
#Tells FastAPI to run your get_session generator function whenever a request arrives and pass its yielded database session into the endpoint.
SessionDep = Annotated[Session, Depends(get_session)] #This line creates a reusable type alias for FastAPI dependency injection. It allows you to cleanly inject a database session into your route handlers without repeating boilerplate code.Without a dependency injection pattern like this, developers often create raw database sessions manually inside every endpoint, leading to messy code and crashed servers under heavy traffic.