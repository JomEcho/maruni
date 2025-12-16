"""
LLMEngine: Gestroomlijnde interface voor systeem-analyse.
Vervangt Bloom's Taxonomy door een System Depth Model (Structuur, Mechanisme, Causaliteit).
"""

import ollama
from typing import Literal, List, Dict

# Nieuw model: System Depth
SystemLevel = Literal["structure", "mechanism", "causality"]

class LLMEngine:
    def __init__(self, model_name: str = "gpt-oss:20b"):
        self.model_name = model_name

    def _get_system_prompt(self, level: SystemLevel) -> str:
        base = """Je bent een System Analyzer.
Jouw doel: De gebruiker helpen een mentaal model van de stof te bouwen.
Stijl: Beknopt, technisch, focussen op logica."""

        instructions = {
            "structure": """
FOCUS: STRUCTUUR & COMPONENTEN
- Vraag naar definities en eigenschappen.
- Vraag naar de hiërarchie (wat is onderdeel van wat?).
- Doel: De statische bouwblokken van het systeem verifiëren.
""",
            "mechanism": """
FOCUS: MECHANISME & PROCES
- Vraag naar het 'hoe'. Hoe werkt het proces?
- Vraag naar de stappen in het systeem.
- Doel: De dynamische werking begrijpen.
""",
            "causality": """
FOCUS: CAUSALITEIT (Oorzaak & Gevolg)
- Vraag naar 'waarom' en 'als-dan' scenario's.
- Vraag naar relaties tussen componenten.
- Doel: Begrijpen hoe variabelen elkaar beïnvloeden.
"""
        }
        return base + "\n" + instructions.get(level, instructions["structure"])

    def _clean_context(self, context_text: str) -> str:
        # Filter metadata en separators
        skip_words = ["drills", "aantekeningen", "samenvatting", "---", "voeg hier"]
        lines = [
            line.strip()
            for line in context_text.split('\n')
            if len(line.strip()) > 5
            and not any(word in line.lower() for word in skip_words)
        ]
        return " ".join(lines)

    def generate_question(self, context_text: str, level: SystemLevel) -> str:
        cleaned = self._clean_context(context_text)
        system = self._get_system_prompt(level)
        
        prompt = f"""
CONTEXT:
{cleaned}

OPDRACHT:
Stel één scherpe vraag die de kennis van de gebruiker test op het gebied van: {level.upper()}.
Gebruik alleen de informatie uit de context. Verzin niets erbij.
"""
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                system=system,
                options={'temperature': 0.2} # Laag voor precisie
            )
            return response['response'].strip()
        except ConnectionError:
            return "⚠️ Kan Ollama niet bereiken. Is de server actief? Start met: ollama serve"
        except Exception as e:
            if "model" in str(e).lower():
                return f"⚠️ Model '{self.model_name}' niet gevonden. Download met: ollama pull {self.model_name}"
            return f"⚠️ Fout bij vraag genereren: {str(e)[:100]}"

    def continue_conversation(self, question: str, context: str, history: List[Dict], user_msg: str, level: SystemLevel) -> str:
        cleaned = self._clean_context(context)
        history_str = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history])
        
        system = self._get_system_prompt(level)
        prompt = f"""
CONTEXT: {cleaned}
VRAAG: {question}
HISTORIE: {history_str}
USER INPUT: {user_msg}

TAAK:
Valideer het antwoord van de gebruiker logisch.
- Klopt de redenatie?
- Zo nee, wijs de logische fout aan.
- Zo ja, bevestig kort.
"""
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                system=system,
                options={'temperature': 0.3}
            )
            return response['response'].strip()
        except ConnectionError:
            return "⚠️ Kan Ollama niet bereiken. Is de server actief?"
        except Exception as e:
            return f"⚠️ Fout bij verwerken: {str(e)[:100]}"

    def generate_multiple_choice_distractors(self, question: str, correct: str) -> List[str]:
        # Genereer plausibele foute opties voor MC mode
        prompt = f"Vraag: {question}\nAntwoord: {correct}\nGenereer 3 foute maar plausibele opties."
        try:
            response = ollama.generate(model=self.model_name, prompt=prompt)
            lines = [l.strip() for l in response['response'].split('\n') if l.strip()]
            # Remove duplicates terwijl volgorde behouden blijft
            unique_lines = list(dict.fromkeys(lines))
            # Zorg dat we minimaal 3 opties hebben
            if len(unique_lines) >= 3:
                return unique_lines[:3]
            else:
                # Fallback als LLM niet genoeg opties geeft
                return unique_lines + ["Optie A", "Optie B", "Optie C"][:3 - len(unique_lines)]
        except:
            return ["Fout A", "Fout B", "Fout C"]