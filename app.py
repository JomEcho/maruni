import streamlit as st
from pathlib import Path
import sys
import random
from thefuzz import fuzz
import time

# Zorg dat Python de src map ziet
sys.path.append(str(Path(__file__).parent))

from src.parser import parse_file
from src.llm_engine import LLMEngine
from src.learning_tracker import (
    record_answer, record_session, select_weighted_drill,
    get_drill_difficulty, get_category_stats, get_file_stats,
    get_progress_data, get_weak_categories, get_drill_stats_for_file,
    check_achievements, get_achievements, get_stats, ACHIEVEMENTS
)

st.set_page_config(page_title="Maruni | Systems", layout="wide", page_icon="🧬")

# Styling
st.markdown("""
<style>
    .stButton>button { border-radius: 4px; }
    h1, h2, h3 { font-family: 'Segoe UI', sans-serif; }
</style>
""", unsafe_allow_html=True)

st.title("🧬 MarUni // Universiteit van Marion")

# Caching
@st.cache_data(show_spinner=False)
def load_data_cached(file_path):
    return parse_file(file_path)

# Init State
defaults = {
    'current_file': None, 'data': None, 'llm_engine': LLMEngine(),
    'score': 0, 'total': 0, 'current_drill': None, 'feedback': None,
    'show_mc': False, 'mc_options': [], 'auto_next': False,
    'ai_question': None, 'chat_history': [],
    'system_level': "structure", # VERANDERD: Van bloom naar system_level
    'selected_category': None, 'context_buffer': "",
    'scores': {},  # Per file: {filename: {"score": 0, "total": 0}}
    'new_achievement': None  # Voor achievement popup
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# Sidebar
with st.sidebar:
    st.header("📂 Input")
    data_dir = Path("data")
    if not data_dir.exists(): st.stop()
    files = sorted([f.name for f in data_dir.glob("*.txt")])
    selected_file = st.selectbox("File:", files, index=None)
    st.divider()
    mode = st.radio("Mode:", ["🎯 Drill (Feiten)", "🧠 System (Logica)"])

    if selected_file and selected_file != st.session_state.current_file:
        st.session_state.current_file = selected_file
        # Laad score voor dit bestand (of start op 0)
        if selected_file in st.session_state.scores:
            st.session_state.score = st.session_state.scores[selected_file]["score"]
            st.session_state.total = st.session_state.scores[selected_file]["total"]
        else:
            st.session_state.score = 0
            st.session_state.total = 0
            st.session_state.scores[selected_file] = {"score": 0, "total": 0}
        st.session_state.ai_question = None
        st.session_state.chat_history = []
        try:
            st.session_state.data = load_data_cached(data_dir / selected_file)
        except Exception as e: st.error(e)

    # Statistieken sectie
    st.divider()
    st.header("📊 Statistieken")

    if selected_file:
        file_stats = get_file_stats(selected_file)
        if file_stats["total"] > 0:
            st.metric("Totaal dit bestand", f"{file_stats['percentage']}%",
                     delta=f"{file_stats['correct']}/{file_stats['total']}")

    # Zwakke punten
    weak = get_weak_categories(3)
    if weak:
        st.markdown("**Zwakke punten:**")
        for cat, pct in weak:
            st.caption(f"• {cat}: {pct:.0f}%")

    # Progressie grafiek
    progress_data = get_progress_data(14)  # Laatste 2 weken
    if progress_data:
        with st.expander("📈 Progressie (14 dagen)"):
            import pandas as pd
            df = pd.DataFrame(progress_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            st.line_chart(df['percentage'], height=150)

    # Achievements
    st.divider()
    achievements = get_achievements()
    total_achievements = len(ACHIEVEMENTS)
    unlocked = len(achievements)

    st.header(f"🏆 Achievements ({unlocked}/{total_achievements})")

    if achievements:
        # Toon unlocked achievements met naam
        for aid, ach in achievements.items():
            st.caption(f"{ach['icon']} **{ach['name']}** - {ach['desc']}")
    else:
        st.caption("Nog geen achievements. Begin met oefenen!")

    # Streak info
    stats = get_stats()
    if stats:
        streak = stats.get('current_streak', 0)
        best = stats.get('best_streak', 0)
        if streak > 0 or best > 0:
            st.caption(f"🔥 Streak: {streak} | Best: {best}")

# Helper: update score en sla op
def update_score(correct: bool):
    st.session_state.total += 1
    if correct:
        st.session_state.score += 1
    # Sync naar scores dict
    if st.session_state.current_file:
        st.session_state.scores[st.session_state.current_file] = {
            "score": st.session_state.score,
            "total": st.session_state.total
        }

# Main Interface
if st.session_state.data:
    data = st.session_state.data

    # Stats
    c1, c2, c3 = st.columns(3)
    c1.metric("Drills", len(data['drills']))
    c2.metric("Contexts", len(data['context']))
    c3.metric("Score", f"{st.session_state.score}/{st.session_state.total}")
    st.divider()

    # --- DRILL MODE ---
    if mode == "🎯 Drill (Feiten)":
        def next_drill():
            if data['drills']:
                # Spaced repetition: selecteer gewogen op basis van historie
                st.session_state.current_drill = select_weighted_drill(
                    data['drills'], st.session_state.current_file
                )
                st.session_state.feedback = None; st.session_state.show_mc = False; st.session_state.mc_options = []

        if not st.session_state.current_drill: next_drill()
        drill = st.session_state.current_drill

        col_q, col_act = st.columns([3, 1])
        with col_q:
            # Moeilijkheidsgraad indicator
            difficulty, pct = get_drill_difficulty(st.session_state.current_file, drill['question'])
            diff_colors = {"Nieuw": "🆕", "Makkelijk": "🟢", "Medium": "🟡", "Moeilijk": "🔴"}
            diff_icon = diff_colors.get(difficulty, "")
            pct_str = f" ({pct:.0f}%)" if pct >= 0 else ""

            st.markdown(f"#### {drill['question']}")
            st.caption(f"{diff_icon} {difficulty}{pct_str} | Categorie: {drill.get('category', 'Algemeen')}")
            if st.session_state.show_mc:
                cols = st.columns(2)
                for i, opt in enumerate(st.session_state.mc_options):
                    if cols[i%2].button(opt, use_container_width=True):
                        is_correct = opt == drill['answer']
                        update_score(is_correct)
                        # Track voor spaced repetition
                        record_answer(
                            st.session_state.current_file,
                            drill['question'],
                            drill.get('category', 'Algemeen'),
                            is_correct
                        )
                        # Check achievements
                        new_achs = check_achievements(is_correct)
                        if new_achs:
                            st.session_state.new_achievement = new_achs[0]
                        if is_correct:
                            st.session_state.feedback = ("success", "Correct")
                        else:
                            st.session_state.feedback = ("error", f"Fout. Antwoord: {drill['answer']}")
                        st.session_state.auto_next = True
                        st.rerun()
            else:
                # Unieke form key per vraag = auto-reset
                form_key = f"drill_{drill['question'][:15]}"
                with st.form(form_key, clear_on_submit=True):
                    inp = st.text_input("Antwoord:", key=f"inp_{drill['question'][:15]}")
                    btn_col1, btn_col2 = st.columns(2)
                    check_clicked = btn_col1.form_submit_button("Check", type="primary")
                    skip_clicked = btn_col2.form_submit_button("🤷 Weet ik niet")

                    if check_clicked:
                        sim = fuzz.ratio(inp.lower(), drill['answer'].lower())
                        is_correct = sim > 85
                        update_score(is_correct)
                        record_answer(
                            st.session_state.current_file,
                            drill['question'],
                            drill.get('category', 'Algemeen'),
                            is_correct
                        )
                        # Check achievements
                        new_achs = check_achievements(is_correct)
                        if new_achs:
                            st.session_state.new_achievement = new_achs[0]
                        if is_correct:
                            st.session_state.feedback = ("success", f"Correct ({sim}%)")
                        else:
                            st.session_state.feedback = ("error", f"Fout. Antwoord: {drill['answer']}")
                        st.session_state.auto_next = True
                        st.rerun()

                    if skip_clicked:
                        update_score(False)
                        record_answer(
                            st.session_state.current_file,
                            drill['question'],
                            drill.get('category', 'Algemeen'),
                            False
                        )
                        # Check achievements (ook bij skip)
                        new_achs = check_achievements(False)
                        if new_achs:
                            st.session_state.new_achievement = new_achs[0]
                        st.session_state.feedback = ("error", f"Antwoord: {drill['answer']}")
                        st.session_state.auto_next = True
                        st.rerun()

        with col_act:
            if st.button("MC Opties"):
                opts = st.session_state.llm_engine.generate_multiple_choice_distractors(drill['question'], drill['answer'])
                opts.append(drill['answer']); random.shuffle(opts)
                st.session_state.mc_options = opts; st.session_state.show_mc = True; st.rerun()
            if st.button("Next"): next_drill(); st.rerun()
            # Keyboard shortcuts hint
            with st.expander("⌨️ Shortcuts"):
                st.caption("**Enter** = Check")
                st.caption("**N** of **Spatie** = Next")
                st.caption("**?** = Weet ik niet")
                st.caption("**1-4** = MC opties")
                st.caption("**Esc** = Focus input")
        
        # Achievement popup met confetti!
        if st.session_state.new_achievement:
            ach_id = st.session_state.new_achievement
            if ach_id in ACHIEVEMENTS:
                ach = ACHIEVEMENTS[ach_id]
                st.balloons()  # Streamlit's ingebouwde confetti
                st.toast(f"{ach['icon']} **{ach['name']}** unlocked!", icon="🎉")
                st.success(f"🏆 **ACHIEVEMENT UNLOCKED!**\n\n{ach['icon']} **{ach['name']}**\n\n_{ach['desc']}_")
            st.session_state.new_achievement = None

        if st.session_state.feedback:
            k, m = st.session_state.feedback
            if k=="success": st.success(m)
            else: st.error(m)
            if st.session_state.auto_next:
                # Langer wachten bij fout antwoord zodat je het kunt lezen
                # Extra tijd als achievement unlocked
                wait_time = 0.8 if k == "success" else 2.5
                time.sleep(wait_time)
                st.session_state.auto_next = False
                next_drill()
                st.rerun()

        # Autofocus + keyboard shortcuts (ALTIJD uitvoeren)
        st.components.v1.html("""
            <script>
            const doc = window.parent.document;

            // Autofocus - altijd proberen
            const focus = () => {
                const inputs = doc.querySelectorAll('input[type="text"]');
                if (inputs.length) {
                    inputs[inputs.length - 1].focus();
                    inputs[inputs.length - 1].select();
                }
            };
            focus();
            setTimeout(focus, 50);
            setTimeout(focus, 150);
            setTimeout(focus, 300);
            setTimeout(focus, 500);
            setTimeout(focus, 800);
            setTimeout(focus, 1200);
            setTimeout(focus, 2000);
            setTimeout(focus, 3000);

            // Keyboard shortcuts (alleen toevoegen als nog niet aanwezig)
            if (!window.maruniKeyboardInit) {
                window.maruniKeyboardInit = true;
                doc.addEventListener('keydown', (e) => {
                    const buttons = doc.querySelectorAll('button');
                    const inputFocused = doc.activeElement.tagName === 'INPUT';

                    // Spatie of N → Next (alleen als niet in inputveld)
                    if ((e.code === 'Space' || e.key === 'n') && !inputFocused) {
                        e.preventDefault();
                        buttons.forEach(btn => {
                            if (btn.innerText.includes('Next')) btn.click();
                        });
                    }

                    // ? → Weet ik niet
                    if (e.key === '?' || (e.key === 's' && !inputFocused)) {
                        buttons.forEach(btn => {
                            if (btn.innerText.includes('Weet ik niet')) btn.click();
                        });
                    }

                    // 1-4 → MC opties
                    if (['1','2','3','4'].includes(e.key) && !inputFocused) {
                        const mcButtons = Array.from(buttons).filter(btn =>
                            !btn.innerText.includes('Next') &&
                            !btn.innerText.includes('MC') &&
                            !btn.innerText.includes('Check') &&
                            !btn.innerText.includes('Weet')
                        );
                        const idx = parseInt(e.key) - 1;
                        if (mcButtons[idx]) mcButtons[idx].click();
                    }

                    // Escape → focus op input
                    if (e.key === 'Escape') {
                        focus();
                    }
                });
            }
            </script>
        """, height=0)

    # --- SYSTEM MODE ---
    else:
        c_p, c_c = st.columns([1, 2])
        with c_p:
            st.markdown("#### Instellingen")
            # Nieuwe Logic Levels
            levels = {
                "structure": "1. Structuur (Componenten)",
                "mechanism": "2. Mechanisme (Werking)",
                "causality": "3. Causaliteit (Oorzaak-Gevolg)"
            }
            lvl = st.selectbox("Diepte:", options=list(levels.keys()), format_func=lambda x: levels[x])
            st.session_state.system_level = lvl

            cat = st.selectbox("Module:", list(data['context'].keys()))
            st.session_state.selected_category = cat

            if st.button("Genereer Vraag", type="primary", use_container_width=True):
                ctx = data['context'][cat]
                st.session_state.context_buffer = ctx
                with st.spinner("Vraag genereren..."):
                    q = st.session_state.llm_engine.generate_question(ctx, lvl)
                    st.session_state.ai_question = q
                    st.session_state.chat_history = []
                    st.rerun()
        
        with c_c:
            if st.session_state.ai_question:
                st.info(f"**Vraag:** {st.session_state.ai_question}")
                for m in st.session_state.chat_history:
                    st.chat_message(m['role']).write(m['content'])
                
                um = st.chat_input("Antwoord...")
                if um:
                    st.session_state.chat_history.append({"role": "user", "content": um})
                    with st.spinner("Evaluating..."):
                        resp = st.session_state.llm_engine.continue_conversation(
                            st.session_state.ai_question,
                            st.session_state.context_buffer,
                            st.session_state.chat_history[:-1],
                            um,
                            st.session_state.system_level
                        )
                    st.session_state.chat_history.append({"role": "assistant", "content": resp})
                    st.rerun()

                # Help buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💡 Geef me een hint", use_container_width=True):
                        st.session_state.chat_history.append({"role": "user", "content": "Hint?"})
                        resp = st.session_state.llm_engine.continue_conversation(
                            st.session_state.ai_question, st.session_state.context_buffer,
                            st.session_state.chat_history[:-1], "Geef een korte hint zonder het antwoord weg te geven.", st.session_state.system_level
                        )
                        st.session_state.chat_history.append({"role": "assistant", "content": resp})
                        st.rerun()
                with col2:
                    if st.button("📖 Toon Antwoord", use_container_width=True):
                        st.session_state.chat_history.append({"role": "user", "content": "Antwoord?"})
                        resp = st.session_state.llm_engine.continue_conversation(
                            st.session_state.ai_question, st.session_state.context_buffer,
                            st.session_state.chat_history[:-1], "Geef het volledige antwoord.", st.session_state.system_level
                        )
                        st.session_state.chat_history.append({"role": "assistant", "content": resp})
                        st.rerun()

                st.divider()

                # Scoring buttons
                col3, col4 = st.columns(2)
                with col3:
                    if st.button("✅ Ik had het goed", type="primary", use_container_width=True):
                        update_score(True)
                        # Start nieuwe vraag
                        ctx = data['context'][st.session_state.selected_category]
                        st.session_state.context_buffer = ctx
                        with st.spinner("Nieuwe vraag..."):
                            q = st.session_state.llm_engine.generate_question(ctx, st.session_state.system_level)
                            st.session_state.ai_question = q
                            st.session_state.chat_history = []
                        st.rerun()
                with col4:
                    if st.button("➡️ Volgende vraag", use_container_width=True):
                        update_score(False)
                        # Start nieuwe vraag
                        ctx = data['context'][st.session_state.selected_category]
                        st.session_state.context_buffer = ctx
                        with st.spinner("Nieuwe vraag..."):
                            q = st.session_state.llm_engine.generate_question(ctx, st.session_state.system_level)
                            st.session_state.ai_question = q
                            st.session_state.chat_history = []
                        st.rerun()
else:
    st.info("Selecteer bestand.")