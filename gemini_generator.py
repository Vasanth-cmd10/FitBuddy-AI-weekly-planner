import os
import logging
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None


def fallback_workout_plan(goal: str, intensity: str) -> str:
    intensity_level = intensity.strip().lower()
    if intensity_level == "beginner":
        sets, reps, rest = "2-3", "10-12", "90 seconds"
    elif intensity_level == "advanced":
        sets, reps, rest = "3-4", "6-12", "2-3 minutes"
    else:
        sets, reps, rest = "3", "8-12", "90-120 seconds"

    goal_lower = goal.lower()
    if "fat" in goal_lower or "loss" in goal_lower:
        goal_focus = "Build or maintain strength while supporting fat loss; finish strength sessions with 10-15 minutes of easy incline walking if recovered."
    elif "endurance" in goal_lower:
        goal_focus = "Build aerobic fitness while maintaining strength; keep most cardio at a pace where you can still speak in short sentences."
    else:
        goal_focus = "Prioritize progressive strength training; add a small amount of weight or repetitions only when every set is controlled."

    days = [
        ("Upper A", ["Machine or dumbbell chest press", "Lat pulldown", "Seated cable row", "Dumbbell shoulder press", "Cable triceps pressdown", "Dumbbell curl"]),
        ("Lower A", ["Goblet squat or leg press", "Dumbbell Romanian deadlift", "Reverse lunge", "Seated leg curl", "Standing calf raise"]),
        ("Cardio and core", ["25-35 minutes easy treadmill, bike, or elliptical", "Dead bug: 3 x 8 per side", "Plank: 3 x 20-40 seconds"]),
        ("Upper B", ["Incline dumbbell press", "Chest-supported row", "Assisted pull-up or pulldown", "Cable lateral raise", "Face pull", "Hammer curl"]),
        ("Lower B", ["Trap-bar deadlift or light Romanian deadlift", "Split squat", "Hip thrust", "Leg extension", "Seated calf raise"]),
        ("Conditioning and accessories", ["20-30 minutes easy cardio", "Cable or machine chest fly: 2-3 x 10-15", "Cable row: 2-3 x 10-15", "Pallof press: 3 x 10 per side"]),
        ("Rest and recovery", ["No structured lifting", "Optional relaxed walk and gentle mobility"]),
    ]

    lines = [
        f"7-Day Gym Workout Plan | Goal: {goal} | Intensity: {intensity}",
        goal_focus,
        f"Strength guidance: {sets} sets of {reps} reps per exercise; rest {rest}. Choose a load that lets you keep good form and finish with 2-3 reps in reserve. For the cardio/core day, use the listed time or reps instead of the strength set target.",
        "",
    ]
    for day_number, (focus, exercises) in enumerate(days, start=1):
        lines.extend([
            f"Day {day_number}: {focus}",
            "Warm-up: 5-8 minutes easy cardio, then 1-2 light practice sets of the first exercise.",
            "Main workout:",
        ])
        lines.extend(f"- {exercise}" for exercise in exercises)
        lines.append("Cooldown: 5 minutes easy walking and comfortable stretching. Stop if you feel sharp pain, dizziness, or unusual shortness of breath.")
        lines.append("")
    lines.append("Adjust the plan to your experience and recovery. If you are new to lifting or have an injury or medical condition, ask a qualified trainer or clinician for modifications.")
    return "\n".join(lines)

def generate_workout_gemini(user_input: dict) -> str:
    goal = user_input["goal"]
    intensity = user_input["intensity"]
    fallback = fallback_workout_plan(goal, intensity)
    if client is None:
        return fallback

    prompt = f"""
You are a qualified gym fitness coach.
Create a safe, practical 7-day gym workout plan for the goal **{goal}** at **{intensity}** intensity.

Each day must include:
- A warm-up (5-10 mins)
- Gym exercises with sets, reps, and rest periods
- A cooldown or recovery tip
- At least one recovery or rest day

Format:
Day X: ...
Warm-up: ...
Main Workout: ...
Cooldown: ...
[Repeat for Day 1-7]
"""
    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview"),
            contents=prompt,
        )
        return response.text.strip() if response.text else fallback
    except Exception as e:
        logging.warning("Gemini workout generation failed; using local plan: %s", e)
        return fallback