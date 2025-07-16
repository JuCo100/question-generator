from flask import Flask, request, jsonify
import requests
import os
import json
import uuid

app = Flask(__name__)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_CYBER_STUDY_API_KEY")
MODEL_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# Load the lesson structure file (must match your nested schema)
with open("/Users/jcohen/Desktop/Question_Generator/security_plus_structure.json", "r") as f:
    data = json.load(f)

# Generate a single multiple choice question
def generate_question(topic_name, subdomain_name, lesson_title, lesson_id):
    system_prompt = (
        "You're an expert AI question generator for cybersecurity certification exams. "
        "Create ONE multiple-choice question (4 options), with a single correct answer, for the lesson described below. "
        "Return only a valid JSON object — no extra text. Fields: question, options, correctAnswer (index), explanation, difficulty (1–10)."
    )

    user_prompt = f"""Topic: {topic_name}
Subdomain: {subdomain_name}
Lesson: {lesson_title}

Output ONLY valid JSON:
{{
  "question": "...",
  "options": ["...", "...", "...", "..."],
  "correctAnswer": 0,
  "explanation": "...",
  "difficulty": 6
}}"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4",
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
            "id": str(uuid.uuid4()),  # use UUID or increment strategy
            "type": "multiple_choice_single",
            "question": parsed["question"],
            "options": parsed["options"],
            "correctAnswer": parsed["correctAnswer"],
            "explanation": parsed["explanation"],
            "difficulty": parsed["difficulty"],
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