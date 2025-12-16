"""
Parser voor leerplatform tekstbestanden.
Splitst bestanden op in drills (flashcards) en context (begripstekst).
"""

from pathlib import Path
from typing import Dict, Any


def parse_file(filepath: Path) -> Dict[str, Any]:
    """
    Parset een tekstbestand naar drills en context.

    Args:
        filepath: Path object naar het te parsen bestand

    Returns:
        Dictionary met:
        - filename: naam van het bestand
        - drills: lijst met drill-objecten (categorie, vraag, antwoord)
        - context: dict met per categorie de context-tekst
    """
    result = {
        "filename": filepath.name,
        "drills": [],
        "context": {}
    }

    current_category = "Algemeen"  # Default categorie
    context_lines = []  # Buffer voor context-tekst per categorie

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        stripped = line.strip()

        # Skip lege regels
        if not stripped:
            continue

        # 1. Header detectie (## ...)
        if stripped.startswith("##"):
            # Als we een nieuwe categorie tegenkomen, sla eerst de oude context op
            if context_lines:
                if current_category not in result["context"]:
                    result["context"][current_category] = ""
                result["context"][current_category] += " ".join(context_lines) + " "
                context_lines = []

            # Nieuwe categorie activeren
            current_category = stripped[2:].strip()
            continue

        # 2. Drill detectie (- ... : ... OF - ... - ...)
        if stripped.startswith("-"):
            # Probeer splits op ':'
            if ":" in stripped:
                parts = stripped[1:].split(":", 1)  # [1:] om de '-' te verwijderen
                question = parts[0].strip()
                answer = parts[1].strip()

                result["drills"].append({
                    "category": current_category,
                    "question": question,
                    "answer": answer
                })
                continue

            # Probeer splits op ' - ' (met spaties eromheen)
            elif " - " in stripped:
                parts = stripped[1:].split(" - ", 1)
                question = parts[0].strip()
                answer = parts[1].strip()

                result["drills"].append({
                    "category": current_category,
                    "question": question,
                    "answer": answer
                })
                continue

        # 3. Skip markdown separators en single # comments
        if stripped == "---" or (stripped.startswith("#") and not stripped.startswith("##")):
            continue

        # 4. Context: alles wat geen header, drill of separator is
        context_lines.append(stripped)

    # Sla resterende context op aan het einde
    if context_lines:
        if current_category not in result["context"]:
            result["context"][current_category] = ""
        result["context"][current_category] += " ".join(context_lines)

    # Cleanup: verwijder lege context entries
    result["context"] = {k: v.strip() for k, v in result["context"].items() if v.strip()}

    return result


if __name__ == "__main__":
    # Zoek alle .txt bestanden in de /data map
    data_dir = Path(__file__).parent.parent / "data"

    if not data_dir.exists():
        print(f"ERROR: Data directory niet gevonden: {data_dir}")
        exit(1)

    txt_files = list(data_dir.glob("*.txt"))

    if not txt_files:
        print(f"Geen .txt bestanden gevonden in {data_dir}")
        exit(0)

    print(f"Gevonden {len(txt_files)} bestand(en) in {data_dir}\n")
    print("=" * 60)

    for filepath in txt_files:
        print(f"\nBestand: {filepath.name}")
        print("-" * 60)

        parsed = parse_file(filepath)

        print(f"  Drills gevonden:  {len(parsed['drills'])}")
        print(f"  Context blokken:  {len(parsed['context'])}")

        if parsed['context']:
            print(f"  Categorieën:      {', '.join(parsed['context'].keys())}")

        # Toon eerste paar drills als voorbeeld
        if parsed['drills']:
            print(f"\n  Eerste drills:")
            for drill in parsed['drills'][:3]:
                print(f"    [{drill['category']}] {drill['question']} → {drill['answer']}")
            if len(parsed['drills']) > 3:
                print(f"    ... en {len(parsed['drills']) - 3} meer")

    print("\n" + "=" * 60)
    print("Parsing voltooid!")
