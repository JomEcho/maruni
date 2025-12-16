"""
Learning Tracker: Spaced repetition en progressie tracking.
Slaat leerdata op in JSON voor persistentie tussen sessies.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math

DATA_FILE = Path(__file__).parent.parent / "user_data.json"


def load_data() -> Dict:
    """Laad gebruikersdata uit JSON."""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return _empty_data()
    return _empty_data()


def _empty_data() -> Dict:
    """Lege datastructuur."""
    return {
        "drills": {},  # drill_id -> {correct, incorrect, last_seen, ease_factor, interval}
        "sessions": [],  # [{date, file, score, total}]
        "categories": {},  # category -> {correct, incorrect}
        "answers_log": [],  # [{date, correct, file, category}] voor progressie tracking
        "achievements": {},  # achievement_id -> {unlocked_at, seen}
        "stats": {  # globale stats voor achievements
            "total_correct": 0,
            "total_incorrect": 0,
            "current_streak": 0,
            "best_streak": 0,
            "session_correct": 0,
            "session_incorrect": 0,
            "days_streak": 0,
            "last_practice_date": None
        }
    }


def save_data(data: Dict) -> None:
    """Sla data op naar JSON."""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_drill_id(file: str, question: str) -> str:
    """Genereer unieke ID voor een drill."""
    return f"{file}::{question[:50]}"


def record_answer(file: str, question: str, category: str, correct: bool) -> None:
    """Registreer een antwoord voor spaced repetition."""
    data = load_data()
    drill_id = get_drill_id(file, question)

    # Init answers_log indien niet aanwezig (backwards compatibility)
    if "answers_log" not in data:
        data["answers_log"] = []

    # Init drill stats indien nieuw
    if drill_id not in data["drills"]:
        data["drills"][drill_id] = {
            "correct": 0,
            "incorrect": 0,
            "last_seen": None,
            "ease_factor": 2.5,  # SM-2 standaard
            "interval": 1,
            "category": category,
            "file": file
        }

    drill = data["drills"][drill_id]
    drill["last_seen"] = datetime.now().isoformat()

    if correct:
        drill["correct"] += 1
        # SM-2: verhoog interval en ease
        drill["ease_factor"] = max(1.3, drill["ease_factor"] + 0.1)
        drill["interval"] = int(drill["interval"] * drill["ease_factor"])
    else:
        drill["incorrect"] += 1
        # SM-2: reset interval, verlaag ease
        drill["ease_factor"] = max(1.3, drill["ease_factor"] - 0.2)
        drill["interval"] = 1

    # Update category stats
    if category not in data["categories"]:
        data["categories"][category] = {"correct": 0, "incorrect": 0}

    if correct:
        data["categories"][category]["correct"] += 1
    else:
        data["categories"][category]["incorrect"] += 1

    # Log voor progressie grafiek
    data["answers_log"].append({
        "date": datetime.now().isoformat(),
        "correct": correct,
        "file": file,
        "category": category
    })
    # Bewaar max 5000 entries
    data["answers_log"] = data["answers_log"][-5000:]

    save_data(data)


def record_session(file: str, score: int, total: int) -> None:
    """Registreer een oefensessie voor progressie tracking."""
    data = load_data()
    data["sessions"].append({
        "date": datetime.now().isoformat(),
        "file": file,
        "score": score,
        "total": total
    })
    # Bewaar max 1000 sessies
    data["sessions"] = data["sessions"][-1000:]
    save_data(data)


def get_drill_weight(file: str, question: str) -> float:
    """
    Bereken gewicht voor drill selectie.
    Hogere weight = moet vaker geoefend worden.
    """
    data = load_data()
    drill_id = get_drill_id(file, question)

    if drill_id not in data["drills"]:
        return 1.0  # Nieuwe drill: normaal gewicht

    drill = data["drills"][drill_id]
    total = drill["correct"] + drill["incorrect"]

    if total == 0:
        return 1.0

    # Basis: percentage fout
    error_rate = drill["incorrect"] / total

    # Factor in tijd sinds laatste keer gezien
    time_factor = 1.0
    if drill["last_seen"]:
        last = datetime.fromisoformat(drill["last_seen"])
        days_ago = (datetime.now() - last).days
        # Als interval verstreken is, verhoog gewicht
        if days_ago >= drill["interval"]:
            time_factor = 1.0 + (days_ago / drill["interval"]) * 0.5

    # Combineer: meer fouten + langer geleden = hoger gewicht
    weight = (0.3 + error_rate * 0.7) * time_factor

    return max(0.1, min(3.0, weight))  # Clamp tussen 0.1 en 3.0


def select_weighted_drill(drills: List[Dict], file: str) -> Dict:
    """Selecteer een drill met spaced repetition weging."""
    import random

    if not drills:
        return None

    weights = [get_drill_weight(file, d["question"]) for d in drills]
    total_weight = sum(weights)

    # Genormaliseerde kansen
    probabilities = [w / total_weight for w in weights]

    # Weighted random selection
    r = random.random()
    cumulative = 0
    for i, p in enumerate(probabilities):
        cumulative += p
        if r <= cumulative:
            return drills[i]

    return drills[-1]


def get_drill_difficulty(file: str, question: str) -> Tuple[str, float]:
    """
    Bereken moeilijkheidsgraad van een drill.
    Returns: (label, percentage_correct)
    """
    data = load_data()
    drill_id = get_drill_id(file, question)

    if drill_id not in data["drills"]:
        return ("Nieuw", -1)

    drill = data["drills"][drill_id]
    total = drill["correct"] + drill["incorrect"]

    if total == 0:
        return ("Nieuw", -1)

    pct = drill["correct"] / total * 100

    if pct >= 80:
        return ("Makkelijk", pct)
    elif pct >= 50:
        return ("Medium", pct)
    else:
        return ("Moeilijk", pct)


def get_category_stats() -> Dict[str, Dict]:
    """Haal statistieken per categorie op."""
    data = load_data()
    stats = {}

    for cat, values in data["categories"].items():
        total = values["correct"] + values["incorrect"]
        if total > 0:
            stats[cat] = {
                "correct": values["correct"],
                "incorrect": values["incorrect"],
                "total": total,
                "percentage": round(values["correct"] / total * 100, 1)
            }

    return stats


def get_file_stats(file: str) -> Dict:
    """Haal statistieken voor een specifiek bestand op."""
    data = load_data()

    correct = 0
    incorrect = 0

    for drill_id, drill in data["drills"].items():
        if drill.get("file") == file:
            correct += drill["correct"]
            incorrect += drill["incorrect"]

    total = correct + incorrect
    return {
        "correct": correct,
        "incorrect": incorrect,
        "total": total,
        "percentage": round(correct / total * 100, 1) if total > 0 else 0
    }


def get_progress_data(days: int = 30) -> List[Dict]:
    """Haal progressie data op voor de laatste N dagen (uit drill history)."""
    data = load_data()
    cutoff = datetime.now() - timedelta(days=days)

    # Groepeer drill pogingen per dag
    daily = {}

    # Gebruik answers_log voor dagelijkse progressie
    if "answers_log" in data:
        for entry in data["answers_log"]:
            entry_date = datetime.fromisoformat(entry["date"])
            if entry_date >= cutoff:
                day_key = entry_date.strftime("%Y-%m-%d")
                if day_key not in daily:
                    daily[day_key] = {"correct": 0, "total": 0}
                daily[day_key]["total"] += 1
                if entry["correct"]:
                    daily[day_key]["correct"] += 1

    # Converteer naar lijst met percentages
    result = []
    for day, values in sorted(daily.items()):
        pct = round(values["correct"] / values["total"] * 100, 1) if values["total"] > 0 else 0
        result.append({
            "date": day,
            "score": values["correct"],
            "total": values["total"],
            "percentage": pct
        })

    return result


def get_weak_categories(limit: int = 5) -> List[Tuple[str, float]]:
    """Vind de zwakste categorieën om te oefenen."""
    stats = get_category_stats()

    # Sorteer op percentage (laag naar hoog), filter minimaal 3 pogingen
    weak = [(cat, s["percentage"]) for cat, s in stats.items() if s["total"] >= 3]
    weak.sort(key=lambda x: x[1])

    return weak[:limit]


def get_drill_stats_for_file(file: str) -> Dict[str, Dict]:
    """Haal alle drill stats op voor een bestand."""
    data = load_data()
    stats = {}

    for drill_id, drill in data["drills"].items():
        if drill.get("file") == file:
            question = drill_id.split("::", 1)[1] if "::" in drill_id else drill_id
            total = drill["correct"] + drill["incorrect"]
            stats[question] = {
                "correct": drill["correct"],
                "incorrect": drill["incorrect"],
                "total": total,
                "percentage": round(drill["correct"] / total * 100, 1) if total > 0 else 0,
                "difficulty": get_drill_difficulty(file, question)[0]
            }

    return stats


# =============================================================================
# ACHIEVEMENTS SYSTEEM
# =============================================================================

ACHIEVEMENTS = {
    "first_blood": {
        "icon": "🏆",
        "name": "First Blood",
        "desc": "Je eerste vraag goed beantwoord"
    },
    "on_fire": {
        "icon": "🔥",
        "name": "On Fire",
        "desc": "10 vragen op rij goed"
    },
    "unstoppable": {
        "icon": "⚡",
        "name": "Unstoppable",
        "desc": "25 vragen op rij goed"
    },
    "big_brain": {
        "icon": "🧠",
        "name": "Big Brain",
        "desc": "100 vragen goed in één sessie"
    },
    "masochist": {
        "icon": "💀",
        "name": "Masochist",
        "desc": "50 keer fout in één sessie"
    },
    "night_owl": {
        "icon": "🦉",
        "name": "Nachtbraker",
        "desc": "Oefenen na middernacht"
    },
    "early_bird": {
        "icon": "☀️",
        "name": "Vroege Vogel",
        "desc": "Oefenen voor 7:00"
    },
    "centurion": {
        "icon": "💯",
        "name": "Centurion",
        "desc": "100 vragen totaal goed"
    },
    "scholar": {
        "icon": "📚",
        "name": "Scholar",
        "desc": "500 vragen totaal goed"
    },
    "master": {
        "icon": "🎓",
        "name": "Master",
        "desc": "1000 vragen totaal goed"
    },
    "streak_week": {
        "icon": "📅",
        "name": "Streaker",
        "desc": "7 dagen op rij geoefend"
    },
    "perfectionist": {
        "icon": "🎯",
        "name": "Perfectionist",
        "desc": "20 vragen op rij goed"
    },
    "comeback": {
        "icon": "💪",
        "name": "Comeback Kid",
        "desc": "Na 5 fouten, 5 goed op rij"
    },
}


def check_achievements(correct: bool) -> List[str]:
    """
    Check of er nieuwe achievements zijn behaald.
    Returns: lijst van nieuw behaalde achievement IDs.
    """
    data = load_data()

    # Init stats als niet aanwezig (backwards compatibility)
    if "stats" not in data:
        data["stats"] = {
            "total_correct": 0, "total_incorrect": 0,
            "current_streak": 0, "best_streak": 0,
            "session_correct": 0, "session_incorrect": 0,
            "days_streak": 0, "last_practice_date": None
        }
    if "achievements" not in data:
        data["achievements"] = {}

    stats = data["stats"]
    now = datetime.now()
    hour = now.hour
    today = now.strftime("%Y-%m-%d")

    # Update stats
    if correct:
        stats["total_correct"] += 1
        stats["session_correct"] += 1
        stats["current_streak"] += 1
        if stats["current_streak"] > stats["best_streak"]:
            stats["best_streak"] = stats["current_streak"]
    else:
        stats["total_incorrect"] += 1
        stats["session_incorrect"] += 1
        stats["current_streak"] = 0

    # Update days streak
    if stats["last_practice_date"] != today:
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        if stats["last_practice_date"] == yesterday:
            stats["days_streak"] += 1
        elif stats["last_practice_date"] is None:
            stats["days_streak"] = 1
        else:
            stats["days_streak"] = 1
        stats["last_practice_date"] = today

    # Check achievements
    new_achievements = []

    def unlock(aid):
        if aid not in data["achievements"]:
            data["achievements"][aid] = {"unlocked_at": now.isoformat(), "seen": False}
            new_achievements.append(aid)

    # First Blood
    if stats["total_correct"] >= 1:
        unlock("first_blood")

    # Streak achievements
    if stats["current_streak"] >= 10:
        unlock("on_fire")
    if stats["current_streak"] >= 20:
        unlock("perfectionist")
    if stats["current_streak"] >= 25:
        unlock("unstoppable")

    # Session achievements
    if stats["session_correct"] >= 100:
        unlock("big_brain")
    if stats["session_incorrect"] >= 50:
        unlock("masochist")

    # Total achievements
    if stats["total_correct"] >= 100:
        unlock("centurion")
    if stats["total_correct"] >= 500:
        unlock("scholar")
    if stats["total_correct"] >= 1000:
        unlock("master")

    # Time-based achievements
    if 0 <= hour < 5:
        unlock("night_owl")
    if 5 <= hour < 7:
        unlock("early_bird")

    # Days streak
    if stats["days_streak"] >= 7:
        unlock("streak_week")

    # Comeback kid: na 5 fouten, nu 5 goed op rij
    if stats["current_streak"] >= 5 and stats["session_incorrect"] >= 5:
        unlock("comeback")

    save_data(data)
    return new_achievements


def get_achievements() -> Dict[str, Dict]:
    """Haal alle behaalde achievements op."""
    data = load_data()
    if "achievements" not in data:
        return {}

    result = {}
    for aid, info in data["achievements"].items():
        if aid in ACHIEVEMENTS:
            result[aid] = {**ACHIEVEMENTS[aid], **info}
    return result


def get_stats() -> Dict:
    """Haal globale stats op."""
    data = load_data()
    if "stats" not in data:
        return {}
    return data["stats"]


def mark_achievement_seen(achievement_id: str) -> None:
    """Markeer achievement als gezien."""
    data = load_data()
    if "achievements" in data and achievement_id in data["achievements"]:
        data["achievements"][achievement_id]["seen"] = True
        save_data(data)


def reset_session_stats() -> None:
    """Reset sessie stats (bij nieuwe sessie)."""
    data = load_data()
    if "stats" in data:
        data["stats"]["session_correct"] = 0
        data["stats"]["session_incorrect"] = 0
        save_data(data)
