from flask import Flask, request, jsonify, send_file
import requests
import os
import json
import uuid
import random

app = Flask(__name__)
OPENROUTER_API_KEY = os.getenv("Question_Generator_Key")
MODEL_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# Load the lesson structure
with open("security_plus_structure.json", "r") as f:
    data = json.load(f)

# System prompt for the model
system_prompt = (
    "You are a custom-tuned AI model specialized in generating HIGH-quality, exam-relevant questions "
    "for cybersecurity certifications such as Security+, CISSP, and AWS Security Specialty. "
    "You will generate ONE multiple-choice question (with exactly 4 answer options) for a specific lesson. "
    "The question should be clear, relevant, and aligned with the certification’s exam style. "
    "Avoid repeating questions that have already been asked. Try a new angle, scenario, or phrasing. "
    "Return ONLY valid JSON — no preamble, no explanation, no markdown. "
    "Each output must include the following fields:\n"
    "• question (string)\n"
    "• options (array of 4 strings)\n"
    "• correctAnswer (integer index of correct option)\n"
    "• explanation (Accurate)\n"
    "• difficulty (1–10)\n"
    "• questionType (currently always 'multiple_choice_single_answer')"
)

def generate_question(topic_name, subdomain_name, lesson_title, lesson_id, existing_questions):
    previous_qs = "\n\n".join(
        [f"Q: {q['question']}\nA: {q['options'][q['correctAnswer']]}" for q in existing_questions]
    )
    if previous_qs:
        previous_qs = f"\nPrevious Questions (avoid repeating these):\n{previous_qs}\n"

    user_prompt = f"""Certification: Security+
Topic: {topic_name}
Subdomain: {subdomain_name}
Lesson: {lesson_title}{previous_qs}

Output ONLY valid JSON:
{{
  "question": "Your question here",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correctAnswer": INDEX_OF_CORRECT_ANSWER,
  "explanation": "Why the correct answer is correct",
  "difficulty": 1–10,
  "questionType": "multiple_choice_single_answer"
}}"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "openai/gpt-4.1",
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
            "type": parsed.get("questionType", "multiple_choice_single_answer"),
            "certification": "Security+",
            "question": parsed["question"],
            "options": parsed["options"],
            "correctAnswer": parsed["correctAnswer"],
            "explanation": parsed["explanation"],
        }

    except Exception as e:
        print("❌ Generation failed:", e)
        return None

@app.route("/generate", methods=["POST"])
def generate_questions():
    questions_per_lesson = int(request.json.get("count", 1))
    generated = 0
    failed = 0

    for topic_index, topic in enumerate(data["topics"], start=1):
        for sub_index, subdomain in enumerate(topic["subdomains"], start=1):
            for lesson_index, lesson in enumerate(subdomain["lessons"], start=1):
                lesson_id = f"sec{topic_index}-{sub_index}-{lesson_index}"
                lesson["lessonID"] = lesson_id  # Ensure it's directly under lessonTitle

                if "questions" not in lesson:
                    lesson["questions"] = []

                for _ in range(questions_per_lesson):
                    q = generate_question(
                        topic_name=topic["topicName"],
                        subdomain_name=subdomain["subdomainName"],
                        lesson_title=lesson["lessonTitle"],
                        lesson_id=lesson_id,
                        existing_questions=lesson["questions"]
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

@app.route("/downloads", methods=["GET"])
def download_questions():
    filepath = "security_plus_full_questions.json"
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({"error": "File not found. Please generate questions first."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)