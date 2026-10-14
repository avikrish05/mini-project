"""CodeLens - Streamlit frontend. Run with: streamlit run frontend.py"""
import json

import streamlit as st
from streamlit import runtime

# If started with the play button or "python frontend.py", restart through Streamlit
if not runtime.exists():
    import subprocess
    import sys
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])
    sys.exit()

from auditor import CodeAuditorEngine

st.set_page_config(page_title="CodeLens", page_icon="🔍", layout="wide")

CREATORS = ["Student name 1", "Student name 2", "Student name 3"]  # <- put your names here
LANGUAGES = ["Auto-detect", "Python", "C++", "C", "Java", "JavaScript",
             "TypeScript", "Go", "Rust", "C#", "PHP", "Ruby"]
ICONS = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}  # also the sort order

ACCENT = "#0E8F8A"  # change this one color to re-theme the whole page
STYLE = """
.stApp { background: linear-gradient(180deg, color-mix(in srgb, ACCENT 10%, transparent), transparent 380px); }
.block-container { max-width: 1200px; padding: 4rem 2rem; }
[data-testid="stVerticalBlock"] { gap: 1.25rem; }
h1 { color: ACCENT; }
h2, h3 { padding-top: 1.25rem !important; }

button[data-baseweb="tab"] { padding: 0.7rem 1.2rem; font-weight: 500; }
button[data-baseweb="tab"][aria-selected="true"],
button[data-baseweb="tab"][aria-selected="true"] p { color: ACCENT; }
[data-baseweb="tab-highlight"] { background-color: ACCENT; height: 3px; }

button[kind="primary"], [data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, ACCENT, color-mix(in srgb, ACCENT 65%, #2563eb));
  border: none; color: #fff; border-radius: 10px; padding: 0.55rem 1.5rem; }
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover { filter: brightness(1.1); color: #fff; }
button[kind="secondary"], [data-testid="stBaseButton-secondary"], [data-testid="stPopover"] button {
  border-radius: 10px; border-color: color-mix(in srgb, ACCENT 45%, transparent); }

[data-testid="stMetric"] {
  background: color-mix(in srgb, ACCENT 7%, transparent);
  border: 1px solid color-mix(in srgb, ACCENT 22%, transparent);
  border-top: 3px solid ACCENT; border-radius: 12px; padding: 0.9rem 1.1rem; }
[data-testid="stExpander"] details { border-radius: 12px; border-color: color-mix(in srgb, ACCENT 25%, transparent); }
[data-testid="stFileUploaderDropzone"] {
  border: 1.5px dashed color-mix(in srgb, ACCENT 55%, transparent);
  border-radius: 12px; background: color-mix(in srgb, ACCENT 5%, transparent); }
[data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within { border-color: ACCENT !important; }
[data-testid="stMarkdownContainer"] blockquote {
  border-left: 4px solid ACCENT; background: color-mix(in srgb, ACCENT 8%, transparent);
  border-radius: 0 10px 10px 0; padding: 0.9rem 1.2rem; }

.bar { height: 10px; border-radius: 99px; overflow: hidden; background: color-mix(in srgb, ACCENT 15%, transparent); }
.bar div { height: 100%; border-radius: 99px; background: linear-gradient(90deg, ACCENT, color-mix(in srgb, ACCENT 60%, #2563eb)); }
"""
st.markdown(f"<style>{STYLE.replace('ACCENT', ACCENT)}</style>", unsafe_allow_html=True)


@st.cache_resource
def get_engine():
    return CodeAuditorEngine()  # created once, reused on every rerun


@st.dialog("About CodeLens")
def about():
    st.markdown("**CS-AI mini project, 2nd year**")
    st.write("CodeLens checks source code for bugs, security problems, and slow logic, "
             "then suggests a cleaner version.")
    st.markdown("**Created by**")
    st.markdown("\n".join(f"- {name}" for name in CREATORS))
    st.caption("Built with Streamlit, Pydantic, and the Gemini API.")


def audit(files, language, notes):
    """Audit every file ({name: code}) and keep the results so they stay on screen."""
    results = {}
    with st.spinner("Auditing your code. This can take up to a minute per file..."):
        for name, code in files.items():
            report = get_engine().audit_snippet(code, language, notes)
            results[name] = (code, report.model_dump(mode="json"))
    st.session_state["results"] = results


def code_viewer(name, code, lang):
    """GitHub-style file box: a header with the file name and size, then numbered code."""
    with st.container(border=True):
        st.markdown(f"📄 **{name}**")
        st.caption(f"{len(code.splitlines())} lines · {len(code.encode()) / 1024:.1f} KB")
        st.code(code, language=lang, line_numbers=True)


def show_report(name, code, r):
    if not r["is_valid_code"]:
        st.warning(r["rejection_reason"] or "The input was not accepted.")
        return

    findings = r["findings"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Health score", f"{r['health_score']} / 100")
    c2.metric("Language", r["language_detected"] or "Unknown")
    c3.metric("Checks passed", r["passed_checks"])
    c4.metric("Issues found", len(findings))
    st.markdown(f'<div class="bar"><div style="width:{r["health_score"]}%"></div></div>',
                unsafe_allow_html=True)
    if r["summary"]:
        st.markdown(f"> {r['summary']}")

    st.subheader("Findings")
    if not findings:
        st.success("No issues found.")
    for f in sorted(findings, key=lambda f: list(ICONS).index(f["severity"])):
        line = f"line {f['line_number']}" if f["line_number"] else "whole file"
        with st.expander(f"{ICONS[f['severity']]} {f['title']} ({f['category']}, {line})",
                         expanded=f["severity"] == "HIGH"):
            st.write(f["description"])
            st.markdown(f"**How to fix it:** {f['suggested_fix']}")

    st.subheader("Complexity")
    st.write(f"**Time:** {r['time_complexity_current']} → {r['time_complexity_optimized']}")
    st.write(f"**Space:** {r['space_complexity_current']} → {r['space_complexity_optimized']}")

    st.subheader("Original and refactored code")
    lang = (r["language_detected"] or "").lower().replace("c++", "cpp").replace("c#", "csharp")
    left, right = st.columns(2)
    with left:
        code_viewer(name, code, lang or None)
    with right:
        code_viewer(f"{name} (refactored)", r["refactored_code"] or "", lang or None)
    st.download_button("Download full report (JSON)", json.dumps(r, indent=2),
                       file_name=f"{name}_report.json", key=f"{name}-json")


# ---------- Page ----------
title_col, model_col, about_col = st.columns([6, 3, 1], vertical_alignment="center")
title_col.title("🔍 CodeLens")
with model_col.popover(f"🤖 {get_engine().model_name}"):
    st.write("Every audit on this page runs on this model through the Gemini API.")
if about_col.button("About"):
    about()

st.write("Paste code or upload files. CodeLens checks them for bugs, security problems, "
         "and slow logic, then suggests a cleaner version.")
st.caption("Health score starts at 100. Each high issue costs 15 points, medium 5, and low 2.")

paste_tab, upload_tab = st.tabs(["Paste code", "Upload files"])

with paste_tab:
    code = st.text_area("Your code", height=300)
    lang1 = st.selectbox("Language", LANGUAGES, key="lang1")
    notes1 = st.text_area("Context for the reviewer (optional)", key="notes1")
    if st.button("Audit code", type="primary"):
        if code.strip():
            audit({"pasted_code": code}, lang1, notes1)
        else:
            st.warning("Paste some code first.")

with upload_tab:
    uploads = st.file_uploader("Source files", accept_multiple_files=True)
    lang2 = st.selectbox("Language", LANGUAGES, key="lang2")
    notes2 = st.text_area("Context for the reviewer (optional)", key="notes2")
    if st.button("Audit files", type="primary"):
        if uploads:
            audit({f.name: f.getvalue().decode("utf-8", errors="replace") for f in uploads},
                  lang2, notes2)
        else:
            st.warning("Choose at least one file first.")

if "results" in st.session_state:
    st.divider()
    st.subheader("Results")
    results = st.session_state["results"]
    for tab, (name, (src, report)) in zip(st.tabs([f"📄 {n}" for n in results]), results.items()):
        with tab:
            show_report(name, src, report)