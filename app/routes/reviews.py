from fastapi import APIRouter
from sqlmodel import Session,select,func
from models import Review,ReviewCreate,ReviewPublic,ReviewUpdate
from database import SessionDep ## without this line, we can't do anything with the database

router=APIRouter(prefix="/review",tags=["reviews"]) ## tags is gonna be used to group routes in the doc (SWAGGER)

@router.get("/",response_model=list[ReviewPublic])  ## because of router, this means "/review/"
def get_reviews(session: SessionDep): # SessionDep helps  access the  database
    return session.exec(select(Review)).all()

#session.add(db_review) is pretty important as it helps us to prepare a transaction; meaning  you can have many "session.add" before committing
@router.post("/", response_model=ReviewPublic)
def create_team(review:ReviewCreate, session: SessionDep): # Session injection, session: SessionDep  is needed for database access Review.model_validate(review) at the runtime
    db_review = Review.model_validate(review) #this line prepare data for the database ; model_validate() skips the dictionary creation step entirely instead of Review(**review.model_dump())
    session.add(db_review) #(Add to cart): places your db_review object into a "staging area" (the session) so SQLModel knows to save it to the database later.
    session.commit()    #(Checkout): This actually executes the SQL INSERT statement and permanently saves the data to your database.
    session.refresh(db_review)
    return db_review #(Get the receipt): After committing, the database automatically generates values like the auto-incrementing id or created_at timestamp. refresh()