from flask import Flask, request, jsonify
import requests
import os
import json
import uuid
import random

app = Flask(__name__)
OPENROUTER_API_KEY = os.getenv("Question_Generator_Key")
MODEL_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# Load the lesson structure
with open("/Users/jcohen/Desktop/Question_Generator/security_plus_structure.json", "r") as f:
    data = json.load(f)

# System prompt for model
system_prompt = (
    "You are a custom-tuned AI model specialized in generating high-quality, exam-relevant questions "
    "for cybersecurity certifications such as Security+, CISSP, and AWS Security Specialty. "
    "You will generate ONE multiple-choice question (with exactly 4 answer options) for a specific lesson. "
    "The question should be clear, relevant, and aligned with the certification’s exam style. "
    "Return ONLY valid JSON — no preamble, no explanation, no markdown. "
    "Each output must include the following fields: \n"
    "• question (string)\n"
    "• options (array of 4 strings)\n"
    "• correctAnswer (integer index of correct option)\n"
    "• explanation (Accurate)\n"
    "• difficulty (1–10, calibrated to the CERTIFICATION’s overall difficulty — Security+ is mid-tier)\n"
    "• questionType (currently always 'multiple_choice_single_answer', but designed for future formats)"
)

# Function to generate a question
def generate_question(topic_name, subdomain_name, lesson_title, lesson_id):
    user_prompt = f"""Certification: Security+
Topic: {topic_name}
Subdomain: {subdomain_name}
Lesson: {lesson_title}

Output only valid JSON:
{{
  "question": "...",
  "options": ["...", "...", "...", "..."],
  "correctAnswer": 0,
  "explanation": "...",
  "difficulty": 6,
  "questionType": "multiple_choice_single"
}}"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "openai/gpt-4-turbo",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    try:
        res = requests.post(MODEL_ENDPOINT, headers=headers, json=payload)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        return {
            "id": str(uuid.uuid4()),
            "type": parsed.get("questionType", "multiple_choice_single"),
            "certification": "Security+",
            "question": parsed["question"],
            "options": parsed["options"],
            "correctAnswer": parsed["correctAnswer"],
            "explanation": parsed["explanation"],
            "difficulty": parsed.get("difficulty", random.randint(3, 8)),
            "lessonID": lesson_id
        }

    except Exception as e:
        print("❌ Generation failed:", e)
        return None

@app.route("/generate", methods=["POST"])
def generate_questions():
    questions_per_lesson = int(request.json.get("count", 1))
    generated = 0
    failed = 0

    for topic in data["topics"]:
        for subdomain in topic["subdomains"]:
            for lesson in subdomain["lessons"]:
                lesson_id = lesson["lessonID"]
                if "questions" not in lesson:
                    lesson["questions"] = []
                for _ in range(questions_per_lesson):
                    q = generate_question(
                        topic_name=topic["topicName"],
                        subdomain_name=subdomain["subdomainName"],
                        lesson_title=lesson["lessonTitle"],
                        lesson_id=lesson_id
                    )
                    if q:
                        lesson["questions"].append(q)
                        generated += 1
                    else:
                        failed += 1

    with open("security_plus_full_questions.json", "w") as f:
        json.dump(data, f, indent=2)

    return jsonify({
        "success": True,
        "generated": generated,
        "failed": failed,
        "message": f"{generated} questions generated and saved."
    })

if __name__ == "__main__":
    app.run(debug=True)