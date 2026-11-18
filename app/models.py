from sqlmodel import SQLModel,Relationship,  Field  # SQLModel specifically build for python
from typing import Optional
from datetime import datetime, timezone
import uuid
import sqlalchemy as sa
"""
Only classes with table=True are database tables managed by Alembic. 
All other classes act purely as Pydantic validation schemas.
Relationship(back_populates="heroes"); it creates symbolic link that is not needed to be part of a payload in post requests

By default, SQLModel automatically converts your PascalCase class name (Team) into a lowercase table name (team) in the database
"""
# 1.Shared properties (used by all models whent it comes to reviews)
class ReviewBase(SQLModel):
    play_name:str = Field(index=True)
    reviewer_name:str
    rating: int=Field(ge=1,le=5)
    comment:str

# 2. Database table model:Review (includes primary key)
class Review(ReviewBase, table=True):
    id : Optional[int] =Field(default=None,primary_key=True) # Optional here means and the instanciation time with new key word, but should be created automatically in the relational database
    created_at:datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# 3. Input schema Review Create (what the client sends in POST)
class ReviewCreate(ReviewBase):
    pass
#the below class acts upon class Review permission read , fields or what should be read
# this could be called ReviewPublic as well

class ReviewPublic(ReviewBase):
    id: int
    created_at:datetime

# fields that can be updated
class ReviewUpdate(SQLModel):
    rating:  Optional[int] =Field(default=None,ge=1,le=5) 
    comment: Optional[str] = None


##extended tables that was  not part of the class
###################################################
##################################################




# ==========================================
# TEAM SCHEMAS & TABLE
# ==========================================
class TeamBase(SQLModel):
    name: str = Field(index=True)
    headquarters: str

#relationship like Relationship(back_populates="team"), should appear only when creating the table Class
class Team(TeamBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    heroes: list["Hero"] = Relationship(back_populates="team")

class TeamCreate(TeamBase):
    """Input schema for POST /teams/ (no id allowed)."""
    pass


class TeamPublic(TeamBase):
    """Output schema for GET/POST responses (guarantees id is present)."""
    id: int
    heroes:list["Hero"]


class TeamUpdate(SQLModel):
    """Input schema for PATCH /teams/{id} (all fields optional)."""
    name: str | None = None
    headquarters: str | None = None


# ==========================================
# HERO SCHEMAS & TABLE
# ==========================================
class HeroBase(SQLModel):
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)
    team_id: int | None = Field(default=None, foreign_key="team.id")


class Hero(HeroBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    team: Team | None = Relationship(back_populates="heroes") # actually, this line is only meant to add a relationship between hero table and team table


class HeroCreate(HeroBase):
    """Input schema for POST /heroes/."""
    pass


class HeroPublic(HeroBase):
    """Output schema for GET/POST responses."""
    id: int


class HeroUpdate(SQLModel):
    """Input schema for PATCH /heroes/{id}."""
    name: str | None = None
    secret_name: str | None = None
    age: int | None = None
    team_id: int | None = None


# ========================================================
# USER PROFILE SCHEMAS & TABLE; ESPECIALLY FOR POSTGRES
# ========================================================
# Supabase (Postgres): Register external 'auth.users' stub so SQLAlchemy resolves the FK.
    # Alembic's include_object filter ensures it is never created or dropped.
sa.Table(
    "users",
    SQLModel.metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    schema="auth",
    extend_existing=True,
    info={"skip_autogenerate": True},  # <-- Tells Alembic: reference only, never create/drop
    )
AUTH_USERS_FK = "auth.users.id"
    
class UserProfileBase(SQLModel):
    username: str | None = Field(default=None, index=True)


class UserProfile(UserProfileBase, table=True):
    __tablename__ = "user_profiles" ## this instead of creating "userprofile" table, we will rathere create "user_profiles"

    id: uuid.UUID = Field(primary_key=True, foreign_key="auth.users.id")
    email: str = Field(index=True, unique=True)


class UserProfilePublic(UserProfileBase):
    """Output schema for GET/PATCH /profiles/me."""
    id: uuid.UUID
    email: str


class UserProfileUpdate(SQLModel):
    """Input schema for PATCH /profiles/me (prevents users from changing id or email)."""
    username: str | None = None 
