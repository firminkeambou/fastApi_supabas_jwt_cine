import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from app.auth import RLSSessionDep
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlmodel import select
from app.database import SessionDep, engine
from app.models import  (Review,ReviewCreate,ReviewPublic,ReviewUpdate,Hero,
    HeroCreate,
    HeroPublic,
    HeroUpdate,
    Team,
    TeamCreate,
    TeamPublic,TeamUpdate,UserProfilePublic,UserProfileUpdate,UserProfile)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Logic ---
    
    # Verify DB connection (Tables are already managed by Alembic)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("Database connection verified.")

    yield  # Application runs here

    # --- Shutdown Logic ---
    engine.dispose()
    print("Database connections closed.")

app = FastAPI(
    title="Cine wouri Reviews API",
    description="Theatre reviews API for Akwa cinema-wouri",
    lifespan=lifespan #method lifespan to be written, handle the life cycle of the app
)

@app.get("/")
def root():
    return {"message":"Welcome to CINE WOURI API"}


# --- TEAMS ---
@app.post("/teams/", response_model=TeamPublic)
def create_team(team: TeamCreate, session: SessionDep):
    db_team = Team.model_validate(team)
    session.add(db_team)
    session.commit()
    session.refresh(db_team)
    return db_team


@app.get("/teams/", response_model=list[TeamPublic])
def read_teams(session: SessionDep):
    return session.exec(select(Team)).all()



# --- HEROES ---
@app.post("/heroes/", response_model=HeroPublic)
def create_hero(hero: HeroCreate, session: SessionDep):
    if hero.team_id is not None:
        if not session.get(Team, hero.team_id):
            raise HTTPException(status_code=404, detail="Team not found")

    db_hero = Hero.model_validate(hero)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero


@app.patch("/heroes/{hero_id}", response_model=HeroPublic)
def update_hero(hero_id: int, hero: HeroUpdate, session: SessionDep):
    db_hero = session.get(Hero, hero_id)
    if not db_hero:
        raise HTTPException(status_code=404, detail="Hero not found")

    # exclude_unset=True ignores fields omitted from the PATCH JSON body
    hero_data = hero.model_dump(exclude_unset=True)
    db_hero.sqlmodel_update(hero_data)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero

#############################################################################
# --- USER PROFILES (RLS-Protected) the below is related to postgres supabase, it will be uncommented out later ---
#----- When a route uses RLSSessionDep, PostgreSQL automatically enforces your RLS policies (USING ((SELECT auth.uid()) = id)) on every query:
#Required Postgres GRANTs for authenticated
#GRANT USAGE ON SCHEMA public TO authenticated;
#GRANT SELECT, UPDATE ON public.user_profiles TO authenticated;
################################################################
@app.get("/profiles/me", response_model=UserProfilePublic)
def get_my_profile(session: RLSSessionDep):
    profile = session.exec(select(UserProfile)).first() 
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.patch("/profiles/me", response_model=UserProfilePublic)
def update_my_profile(profile_update: UserProfileUpdate, session: RLSSessionDep):
    """UPDATE MY PROFILE USERNAME """
    db_profile = session.exec(select(UserProfile)).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = profile_update.model_dump(exclude_unset=True)  ## Pydantic/SQLModel update schema into a Python dictionary containing only the fields that were explicitly provided by the client.
    db_profile.sqlmodel_update(update_data)  # updates an existing SQLModel database instance in place using a dictionary or another model.
    session.add(db_profile) #Registers the object in the session,No database query is executed yet.afe to call on already-tracked objects 
    session.flush() # session.commit() is the correct choice except it was part of a transaction, in this case,     session.flush() is the best
    session.refresh(db_profile) #Fetches database-generated values,Prevents errors after the session closes
    return db_profile  
