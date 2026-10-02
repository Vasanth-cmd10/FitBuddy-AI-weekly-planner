from pydantic import BaseModel

class UserInput(BaseModel):
    user_id: int
    username: str
    age: int
    weight: float
    goal: str
    intensity: str

class WorkoutRequest(BaseModel):
    goal: str
    intensity: str

class FeedbackRequest(BaseModel):
    feedback: str