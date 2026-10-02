import os
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///./fitbuddy.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer)
    weight = Column(Float)
    goal = Column(String)
    intensity = Column(String)
    schedule = Column(Integer, default=7)
    
    plans = relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan")

class WorkoutPlan(Base):
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    original_plan = Column(Text)
    updated_plan = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="plans")

def init_db():
    Base.metadata.create_all(bind=engine)

def save_user(name: str, age: int, weight: float, goal: str, intensity: str) -> int:
    db = SessionLocal()
    try:
        user = User(
            name=name,
            age=age,
            weight=weight,
            goal=goal,
            intensity=intensity,
            schedule=7
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
    finally:
        db.close()

def save_plan(user_id: int, plan: str):
    db = SessionLocal()
    # Check if a plan already exists for this user
    existing_plan = db.query(WorkoutPlan).filter_by(user_id=user_id).first()
    if existing_plan:
        existing_plan.original_plan = plan
    else:
        workout = WorkoutPlan(user_id=user_id, original_plan=plan)
        db.add(workout)
    db.commit()
    db.close()

def update_plan(user_id: int, updated_text: str):
    db = SessionLocal()
    workout = db.query(WorkoutPlan).filter_by(user_id=user_id).first()
    if workout:
        workout.updated_plan = updated_text
        db.commit()
    db.close()

def get_original_plan(user_id: int):
    db = SessionLocal()
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).first()
    db.close()
    return plan.original_plan if plan else None

def get_user(user_id: int):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    return user