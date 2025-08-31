# ai_engine.py (Gemini version - cleaned formatting)
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-1.5-flash")

def process_transcript(transcript: str):
    prompt = f"""
    You are an assistant that summarizes meetings.
    Transcript:
    {transcript}

    Provide:
    1. Concise summary (5 bullet points).
    2. Action items grouped by person in JSON format:
       {{
         "Person1": ["Task 1", "Task 2"],
         "Person2": ["Task A"]
       }}
    """

    response = model.generate_content(prompt)
    text_output = response.text

    # --- Extract JSON for action items ---
    summary_text = text_output
    tasks_json = {}
    try:
        start = text_output.index("{")
        end = text_output.rindex("}") + 1
        tasks_json = json.loads(text_output[start:end])
        summary_text = text_output[:start].strip()
    except Exception:
        tasks_json = {}

    # --- Format for end user ---
    formatted_output = ""
    for line in summary_text.splitlines():
        if line.strip():
            formatted_output += f"{line.strip().lstrip('*- ').strip()}\n"

    if tasks_json:
        formatted_output += "\nAction Items\n"
        for person, tasks in tasks_json.items():
            formatted_output += f"{person}\n"
            for task in tasks:
                formatted_output += f"{task}\n"

    # Return BOTH (for Flask unpacking)
    return formatted_output, tasks_json
