import json, os
from core.settings import settings

DEFAULT = {
    "language": settings.LANG,
    "session_minutes": settings.SESSION_MINUTES,
    "prefer_multiple_choice_for_calibration": True,
    "open_question_depth": "kort",
    "always_include_waarom": True,
    "structure_preferences": ["kern eerst", "waarom", "stap-voor-stap", "definitie → voorbeeld → valkuil"],
    "ui_preferences": {"show_confidence_slider": True, "show_time_goals": True, "concise_mode": True},
    "llm_style_directives": [
        "Antwoord in het Nederlands.",
        "Wees kort en precies: geef de kern + de waarom.",
        "Gebruik genummerde stappen waar nuttig; noem valkuilen."
    ],
}

def load_profile(path: str = "config/learner_profile.yaml") -> dict:
    if not os.path.exists(path):
        return DEFAULT
    try:
        # it's JSON-compatible YAML
        text = open(path, "r", encoding="utf-8").read()
        data = json.loads(text)
        return {**DEFAULT, **data}
    except Exception:
        return DEFAULT

PROFILE = load_profile()
