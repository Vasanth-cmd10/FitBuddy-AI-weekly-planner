import logging

from fastapi import APIRouter, BackgroundTasks, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from app.database import SessionLocal, save_user, save_plan, update_plan, get_original_plan, User, WorkoutPlan
from app.schemas import UserInput, WorkoutRequest, FeedbackRequest
from app.gemini_generator import generate_workout_gemini, fallback_workout_plan
from app.gemini_flash_generator import generate_nutrition_tip_with_flash, fallback_nutrition_tip
from app.updated_plan import update_workout_plan

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(os.path.dirname(BASE_DIR), "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)
_plan_generation_status: dict[int, dict[str, str]] = {}


def _is_saved_plan_error(plan_text: str | None) -> bool:
    if not plan_text:
        return False
    return (
        plan_text.lstrip().startswith(("Error:", "Error updating plan:"))
        or "404 NOT_FOUND" in plan_text
    )


def _generate_plan_in_background(user_id: int, goal: str, intensity: str):
    try:
        workout_plan = generate_workout_gemini({"goal": goal, "intensity": intensity})
        nutrition_tip = generate_nutrition_tip_with_flash(goal)
        save_plan(user_id, workout_plan)
        _plan_generation_status[user_id] = {
            "status": "complete",
            "workout_plan": workout_plan,
            "nutrition_tip": nutrition_tip,
        }
    except Exception:
        logging.exception("Background plan generation failed for user %s", user_id)
        _plan_generation_status[user_id] = {"status": "failed"}

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/generate-workout", response_class=HTMLResponse)
async def generate_workout_web(
    request: Request,
    background_tasks: BackgroundTasks,
    username: str = Form(...),
    age: int = Form(...),
    weight: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...)
):
    try:
        user_id = save_user(username, age, weight, goal, intensity)

        workout_plan = fallback_workout_plan(goal, intensity)
        nutrition_tip = fallback_nutrition_tip(goal)
        save_plan(user_id, workout_plan)
        _plan_generation_status[user_id] = {"status": "pending"}
        background_tasks.add_task(_generate_plan_in_background, user_id, goal, intensity)
        
        return templates.TemplateResponse("result.html", {
            "request": request,
            "username": username,
            "user_id": user_id,
            "age": age,
            "weight": weight,
            "goal": goal,
            "intensity": intensity,
            "workout_plan": workout_plan,
            "nutrition_tip": nutrition_tip,
            "generation_pending": True
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan-status/{user_id}")
def get_plan_generation_status(user_id: int):
    return _plan_generation_status.get(user_id, {"status": "unavailable"})

@router.post("/submit-feedback", response_class=HTMLResponse)
async def submit_feedback(
    request: Request,
    user_id: int = Form(...),
    feedback: str = Form(...)
):
    original = get_original_plan(user_id)
    if not original:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "error": "Original plan not found for this user ID.",
            "workout_plan": "",
            "nutrition_tip": ""
        })
    
    updated = update_workout_plan(original, feedback)
    if updated:
        update_plan(user_id, updated)
    
    db = SessionLocal()
    user = db.query(User).filter_by(id=user_id).first()
    db.close()
    
    return templates.TemplateResponse("result.html", {
        "request": request,
        "username": user.name if user else "User",
        "user_id": user_id,
        "age": user.age if user else 0,
        "weight": user.weight if user else 0.0,
        "goal": user.goal if user else "",
        "intensity": user.intensity if user else "",
        "workout_plan": updated or original,
        "nutrition_tip": "Review your updated plan based on feedback!",
        "success_message": "Your plan has been updated based on feedback!" if updated else None,
        "warning_message": None if updated else "The AI service could not apply your feedback right now. Your saved workout plan has been kept unchanged. Please try again later."
    })

@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request):
    db = SessionLocal()
    users = db.query(User).all()
    user_data = []
    for user in users:
        plan = db.query(WorkoutPlan).filter_by(user_id=user.id).first()
        original_plan = plan.original_plan if plan else "N/A"
        if plan and _is_saved_plan_error(original_plan):
            original_plan = fallback_workout_plan(user.goal, user.intensity)

        updated_plan = plan.updated_plan if plan else None
        if _is_saved_plan_error(updated_plan):
            updated_plan = None

        user_data.append({
            "id": user.id,
            "name": user.name,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity,
            "original_plan": original_plan,
            "updated_plan": updated_plan or "No successful update saved"
        })
    db.close()
    return templates.TemplateResponse("all_users.html", {
        "request": request,
        "users": user_data
    })