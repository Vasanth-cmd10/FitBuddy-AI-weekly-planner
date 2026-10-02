import os
import logging
import re
from typing import Optional
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None


def _local_feedback_update(original_plan: str, feedback: str) -> str:
    request = feedback.strip()
    normalized = request.lower()

    if re.search(r"cardio|conditioning|treadmill|running|cycling|bike|elliptical", normalized):
        adjustment = "Add two 15-minute low-impact cardio finishers after upper-body sessions. Use an incline walk, bike, or elliptical at a pace where you can still speak comfortably. Keep the existing conditioning day easy."
    elif re.search(r"rest|recovery|tired|fatigue|sore|overtrain", normalized):
        adjustment = "Replace the next conditioning or accessory day with a full rest day. An easy walk and gentle mobility are optional; do not make up missed sets. Resume lifting when you feel recovered."
    elif re.search(r"easier|beginner|too hard|reduce|lighter|less intense", normalized):
        adjustment = "For the next week, do two working sets per exercise and choose loads that leave 3-4 good reps in reserve. Keep every rep controlled, then return to the listed volume gradually if recovery is good."
    elif re.search(r"harder|more challenging|more volume|more sets|strength|muscle|hypertrophy", normalized):
        adjustment = "Keep the current exercise selection and add one working set to the first two main lifts on each strength day. Leave 1-2 good reps in reserve; increase weight only after you can complete all prescribed reps with clean form."
    elif re.search(r"leg|quad|hamstring|glute", normalized):
        adjustment = "Add 2 sets of 10-12 controlled leg extensions or hamstring curls to one lower-body day. Start light and remove the extra work if it affects recovery or causes pain."
    elif re.search(r"chest|pec", normalized):
        adjustment = "Add 2 sets of 10-12 light cable or machine chest flyes to one upper-body day, after your presses. Stop each set with 2-3 good reps still possible."
    elif re.search(r"back|lat|row", normalized):
        adjustment = "Add 2 sets of 10-12 chest-supported rows to one upper-body day. Use a controlled range of motion and avoid swinging the weight."
    elif re.search(r"shoulder|delt", normalized):
        adjustment = "Add 2 sets of 12-15 light cable or dumbbell lateral raises to one upper-body day. Keep the movement controlled and pain-free."
    else:
        adjustment = "Keep the current schedule and make one small change at a time. Choose a load that allows controlled reps with 2-3 reps in reserve, and stop any exercise that causes sharp pain. For an equipment substitution, name the exercise and equipment you have available."

    return f"{original_plan.rstrip()}\n\nCoach Update Based on Your Feedback\nYour request: {request}\nAdjustment: {adjustment}"


def update_workout_plan(original_plan: str, user_feedback: str) -> Optional[str]:
    """
    Revise a gym plan with Gemini or a practical local coach adjustment.
    """
    prompt = f"""
You are a professional fitness trainer assistant.

Here's the original 7-day workout plan:
{original_plan}

User Feedback:
"{user_feedback}"

Based on the feedback, revise the relevant parts of the workout plan. Keep the format and rest of the plan unchanged if not needed.
"""
    if client is None:
        return _local_feedback_update(original_plan, user_feedback)

    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview"),
            contents=prompt,
        )
        return response.text.strip() if response.text else None
    except Exception as e:
        logging.warning("Gemini plan update failed; applying a local coach adjustment: %s", e)
        return _local_feedback_update(original_plan, user_feedback)