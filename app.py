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

st.set_page_config(page_title="Maruni | Systems", layout="wide", page_icon="🧬")

# Styling
st.markdown("""
<style>
    .stButton>button { border-radius: 4px; }
    h1, h2, h3 { font-family: 'Segoe UI', sans-serif; }
</style>
""", unsafe_allow_html=True)

st.title("🧬 Maruni // System Core")

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
    'scores': {}  # Per file: {filename: {"score": 0, "total": 0}}
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
                st.session_state.current_drill = random.choice(data['drills'])
                st.session_state.feedback = None; st.session_state.show_mc = False; st.session_state.mc_options = []
        
        if not st.session_state.current_drill: next_drill()
        drill = st.session_state.current_drill

        col_q, col_act = st.columns([3, 1])
        with col_q:
            st.markdown(f"#### {drill['question']}")
            if st.session_state.show_mc:
                cols = st.columns(2)
                for i, opt in enumerate(st.session_state.mc_options):
                    if cols[i%2].button(opt, use_container_width=True):
                        is_correct = opt == drill['answer']
                        update_score(is_correct)
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
                    if st.form_submit_button("Check"):
                        sim = fuzz.ratio(inp.lower(), drill['answer'].lower())
                        is_correct = sim > 85
                        update_score(is_correct)
                        if is_correct:
                            st.session_state.feedback = ("success", f"Correct ({sim}%)")
                        else:
                            st.session_state.feedback = ("error", f"Fout. Antwoord: {drill['answer']}")
                        st.session_state.auto_next = True
                        st.rerun()

                # Aggressive autofocus
                st.components.v1.html("""
                    <script>
                    const focus = () => {
                        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
                        if (inputs.length) inputs[inputs.length - 1].focus();
                    };
                    focus();
                    setTimeout(focus, 50);
                    setTimeout(focus, 150);
                    setTimeout(focus, 400);
                    </script>
                """, height=0)

        with col_act:
            if st.button("MC Opties"):
                opts = st.session_state.llm_engine.generate_multiple_choice_distractors(drill['question'], drill['answer'])
                opts.append(drill['answer']); random.shuffle(opts)
                st.session_state.mc_options = opts; st.session_state.show_mc = True; st.rerun()
            if st.button("Next"): next_drill(); st.rerun()
        
        if st.session_state.feedback:
            k, m = st.session_state.feedback
            if k=="success": st.success(m)
            else: st.error(m)
            if st.session_state.auto_next: time.sleep(1.0); st.session_state.auto_next=False; next_drill(); st.rerun()

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