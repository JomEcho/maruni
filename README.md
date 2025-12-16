# Maruni - Slim Leerplatform

Een persoonlijk leerplatform dat je helpt om feiten en inzichten te onthouden met behulp van **spaced repetition** (slim herhalen).

---

## Wat doet Maruni?

Maruni is een quiz-app met twee manieren van leren:

### 1. Drill Mode (Feiten)
Snelle vraag-en-antwoord oefeningen. Je typt het antwoord en het systeem checkt of het goed is (kleine typefouten worden geaccepteerd).

**Slim herhalen:** Vragen die je fout beantwoordt komen vaker terug. Vragen die je goed kent zie je minder vaak. Zo besteed je tijd aan wat je nog moet leren.

### 2. System Mode (Logica)
Een AI stelt diepere vragen over de stof op drie niveaus:
- **Structuur**: Wat zijn de onderdelen?
- **Mechanisme**: Hoe werkt het?
- **Causaliteit**: Waarom? Wat als...?

> Let op: System Mode vereist [Ollama](https://ollama.ai) (lokale AI).

---

## Snel starten

```bash
# 1. Installeer dependencies
pip install -r requirements.txt

# 2. Start de app
streamlit run app.py

# 3. Open in browser
# http://localhost:8501
```

---

## Hoe werkt het?

### Je eigen leerstof toevoegen

Maak een `.txt` bestand in de `data/` map. Gebruik dit formaat:

```
## Categorienaam

Hier schrijf je context/uitleg over het onderwerp.
Dit wordt gebruikt voor System Mode vragen.

- Vraag hier?: antwoord hier
- Wat is de hoofdstad van Nederland?: Amsterdam
- Hoeveel planeten heeft ons zonnestelsel?: 8
```

**Regels:**
- `## Titel` = nieuwe categorie
- `- vraag?: antwoord` = een drill (flashcard)
- Alle andere tekst = context voor AI vragen

---

## Projectstructuur

```
maruni/
├── app.py                 # Hoofdapplicatie (Streamlit)
├── requirements.txt       # Python dependencies
├── user_data.json         # Jouw leervoortgang (automatisch aangemaakt)
├── data/                  # Leerstof bestanden
│   ├── astr.txt          # Astronomie
│   ├── chem.txt          # Scheikunde
│   └── hist_tech.txt     # Technische geschiedenis
└── src/                   # Broncode modules
    ├── parser.py         # Leest tekstbestanden
    ├── llm_engine.py     # AI vraag generator
    └── learning_tracker.py # Spaced repetition systeem
```

---

## De bestanden uitgelegd

### `app.py` - De hoofdapplicatie

Dit is het startpunt van de app. Het gebruikt **Streamlit** om een webinterface te maken.

**Wat het doet:**
1. Toont een sidebar met bestandskeuze en statistieken
2. Laadt je leerstof uit tekstbestanden
3. Drill Mode: toont vragen, checkt antwoorden, houdt score bij
4. System Mode: laat de AI vragen genereren

**Belangrijke onderdelen:**
- `st.session_state` = onthoudt data tussen pagina-refreshes
- `st.form` = het invoerveld + knoppen voor antwoorden
- `update_score()` = houdt je score bij
- `next_drill()` = kiest de volgende vraag (met slim herhalen)

---

### `src/parser.py` - Tekstbestanden lezen

Leest `.txt` bestanden en splitst ze op in:
- **Drills**: vraag-antwoord paren (regels die beginnen met `-`)
- **Context**: uitleg tekst (voor AI vragen)

**Voorbeeld input:**
```
## Planeten
De aarde draait om de zon.
- Hoeveel planeten?: 8
```

**Output:**
```python
{
    "drills": [{"category": "Planeten", "question": "Hoeveel planeten?", "answer": "8"}],
    "context": {"Planeten": "De aarde draait om de zon."}
}
```

---

### `src/llm_engine.py` - AI vraag generator

Gebruikt **Ollama** (lokale AI) om slimme vragen te stellen.

**Functies:**
- `generate_question()` = maakt een vraag op basis van context
- `continue_conversation()` = evalueert je antwoord
- `generate_multiple_choice_distractors()` = maakt foute opties voor MC

**System Levels:**
- `structure` = vraagt naar onderdelen en definities
- `mechanism` = vraagt naar hoe iets werkt
- `causality` = vraagt naar oorzaak en gevolg

---

### `src/learning_tracker.py` - Slim herhalen

Het hart van het spaced repetition systeem. Slaat alles op in `user_data.json`.

**Wat het bijhoudt per vraag:**
- Hoe vaak goed/fout beantwoord
- Wanneer laatst gezien
- `ease_factor` = hoe makkelijk de vraag is (start op 2.5)
- `interval` = hoeveel dagen tot volgende herhaling

**Het SM-2 algoritme (versimpeld):**
```
Als je GOED antwoordt:
    → ease_factor omhoog (+0.1)
    → interval wordt langer (× ease_factor)
    → Je ziet de vraag minder vaak

Als je FOUT antwoordt:
    → ease_factor omlaag (-0.2)
    → interval reset naar 1
    → Je ziet de vraag vaker
```

**Belangrijke functies:**
- `record_answer()` = slaat een antwoord op
- `select_weighted_drill()` = kiest volgende vraag (moeilijke vragen = hogere kans)
- `get_drill_difficulty()` = berekent of vraag makkelijk/medium/moeilijk is
- `get_category_stats()` = statistieken per categorie
- `get_progress_data()` = data voor de voortgangsgrafiek

---

## Dependencies

| Package | Waarvoor |
|---------|----------|
| `streamlit` | Web interface |
| `thefuzz` | Fuzzy matching (kleine typefouten accepteren) |
| `pandas` | Data voor grafieken |
| `ollama` | Lokale AI (alleen voor System Mode) |

---

## Tips

1. **Begin met Drill Mode** - System Mode is leuk maar Drill Mode is effectiever voor feiten leren

2. **Wees consistent** - Spaced repetition werkt het beste als je regelmatig oefent

3. **Voeg eigen stof toe** - Maak je eigen `.txt` bestanden voor wat je wilt leren

4. **Let op de kleuren**:
   - 🆕 Nieuw = nog niet geoefend
   - 🟢 Makkelijk = >80% goed
   - 🟡 Medium = 50-80% goed
   - 🔴 Moeilijk = <50% goed

---

## Veelgestelde vragen

**Q: Waarom werkt System Mode niet?**
A: Je hebt Ollama nodig. Installeer het van [ollama.ai](https://ollama.ai) en run `ollama pull gpt-oss:20b`.

**Q: Waar wordt mijn voortgang opgeslagen?**
A: In `user_data.json` in de hoofdmap. Dit bestand wordt automatisch aangemaakt.

**Q: Hoe reset ik mijn voortgang?**
A: Verwijder `user_data.json`. Bij de volgende start begin je opnieuw.

**Q: Kan ik de wachttijd na een fout antwoord aanpassen?**
A: Ja, in `app.py` rond regel 235. Verander `2.5` naar wat je wilt.

---

## Toekomstige ideeën

Features die nog gebouwd kunnen worden:

### Auto-generate drills
Een knop die automatisch drills genereert uit je context-tekst via de LLM. Je schrijft alleen de kennistekst, de AI maakt vraag-antwoord paren.

```python
# Nieuwe functie in llm_engine.py
def generate_drills_from_context(context: str) -> List[Dict]:
    """Genereert vraag-antwoord paren uit een stuk tekst."""
    prompt = f"Maak flashcard vragen van deze tekst: {context}"
    # ... LLM call ...
    return [{"question": "...", "answer": "..."}]
```

### Reverse drills
Automatisch de omgekeerde vraag genereren. "Amsterdam is de hoofdstad van?" wordt ook "Wat is de hoofdstad van Nederland?".

### Streaks & dagelijkse doelen
Bijhouden hoeveel dagen op rij je hebt geoefend. Dagelijks doel instellen (bijv. 20 vragen per dag).

### Quiz modus
Timer + highscores. Race tegen de klok!

### Multiplayer
Samen met vrienden quizzen, wie scoort het hoogst?

### Export naar Anki
Je drills exporteren naar het populaire Anki flashcard formaat.

### Mobiele app / PWA
Progressive Web App maken zodat Maruni als app op je telefoon werkt.
