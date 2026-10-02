import os
import logging
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None


def fallback_nutrition_tip(goal: str) -> str:
    goal_lower = goal.lower()
    if "fat" in goal_lower or "loss" in goal_lower:
        return "Gym nutrition tip: To support fat loss while keeping strength, build meals around a protein source and vegetables, and choose a portion size you can sustain. Drink water before training; supplements are not required."
    if "endurance" in goal_lower:
        return "Gym nutrition tip: For a longer or harder cardio session, have an easy-to-digest carbohydrate snack beforehand and drink water. Afterward, have a meal with carbohydrates and protein to replenish energy and support recovery."
    return "Gym nutrition tip: Support muscle growth by eating enough across the day, including a protein-rich food at each meal. After lifting, a normal meal with protein and carbohydrates is a practical recovery choice; consistency matters more than a special supplement."

def generate_nutrition_tip_with_flash(goal: str) -> str:
    """
    Generate a nutrition or recovery tip using Gemini Flash based on the user's fitness goal.
    """
    fallback = fallback_nutrition_tip(goal)
    if client is None:
        return fallback

    prompt = (
        f"Give one practical gym nutrition or workout-recovery tip for someone whose fitness goal is '{goal}'. "
        "Keep it safe, evidence-informed, friendly, and easy to follow. Do not recommend supplements as necessary."
    )
    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            contents=prompt,
        )
        return response.text.strip() if response.text else fallback
    except Exception as e:
        logging.warning("Gemini nutrition generation failed; using local tip: %s", e)
        return fallback