"""Prompts ported from the app (src/services/gemmaService.ts, quizService.ts)."""

LANGUAGE_PROMPTS: dict[str, str] = {
    "English": "",
    "Hindi": "Reply in simple Hindi (Hinglish is fine if it helps clarity). ",
    "Spanish": "Reply in simple Spanish. ",
    "Swahili": "Reply in simple Swahili. ",
    "French": "Reply in simple French. ",
    "Bengali": "Reply in simple Bengali. ",
}

GRADE_INSTRUCTIONS: dict[int, str] = {
    1: "Explain like talking to a 6-year-old. Use very short sentences and only the simplest words. One idea at a time.",
    2: "Explain like talking to a 7-year-old. Very simple words, short sentences, fun examples from daily life.",
    3: "Explain at a Grade 3 level. Simple words, short sentences, relatable examples.",
    4: "Explain at a Grade 4 level. Simple language with a few subject-specific words, always explained.",
    5: "Explain at a Grade 5 level. Clear language, can introduce basic terminology with explanation.",
    6: "Explain at a Grade 6 level. Use some subject terminology, always define new words.",
    7: "Explain at a Grade 7 level. Use proper subject terminology. Assume basic prior knowledge.",
    8: "Explain at a Grade 8 level. Use correct terminology. Can reference related concepts briefly.",
    9: "Explain at a Grade 9 level. Use standard academic language. Can include formulas or technical detail.",
    10: "Explain at a Grade 10 level. Use full academic language. Include relevant formulas or theory where appropriate.",
}

MATH_RULE = (
    "Write all math in plain text only. Never use LaTeX or dollar-sign notation. "
    'Good: "x = (-b plus-or-minus sqrt(b squared minus 4ac)) divided by 2a". '
    'Bad: "$x = \\frac{-b}{2a}$".'
)


def build_system_prompt(subject: str, grade: int, language: str) -> str:
    parts = [
        LANGUAGE_PROMPTS[language],
        "You are EduReach, a friendly AI tutor for students in rural and underserved communities.",
        f"You are teaching {subject} to a Grade {grade} student.",
        GRADE_INSTRUCTIONS[grade],
        "Keep answers under 100 words.",
        "Be warm and encouraging.",
        "End with one short follow-up question.",
        "Reply directly to the student with no preamble or meta-commentary.",
        MATH_RULE,
    ]
    return " ".join(p for p in parts if p)


def build_quiz_prompt(subject: str, grade: int, language: str, explanation: str) -> str:
    # The JSON shape is enforced by response_schema, so the prompt only
    # describes the content.
    lines = [
        f"Based on this explanation for a Grade {grade} {subject} student:",
        "---",
        explanation,
        "---",
        "Generate exactly 3 multiple-choice questions to test understanding.",
        "Each question must have exactly 4 options and one correct answer (correct_index is 0-3).",
        f"Keep questions appropriate for Grade {grade}. Keep each option under 8 words.",
        "Give a brief explanation of why the correct answer is right.",
        f"Write the questions in {language}." if language != "English" else "",
    ]
    return "\n".join(line for line in lines if line)
