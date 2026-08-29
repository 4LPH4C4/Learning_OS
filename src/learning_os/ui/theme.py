from __future__ import annotations

import streamlit as st


CSS = """
<style>
:root {
  --ink: #14213d;
  --muted: #667085;
  --line: #e7eaf0;
  --paper: #fbfaf7;
  --accent: #3454d1;
  --accent-soft: #eef1ff;
  --success: #138a61;
}

.stApp { background: var(--paper); color: var(--ink); }
html, body, [class*="css"], [data-testid="stAppViewContainer"] {
  font-family: Inter, Pretendard, "Noto Sans KR", "Segoe UI", sans-serif;
}
[data-testid="stHeader"] { background: rgba(251,250,247,.88); }
[data-testid="stSidebar"] { background: #f3f1ec; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] hr { border-color: #ddd9d0; }
.block-container { max-width: 1120px; padding-top: 2.8rem; padding-bottom: 5rem; }
h1, h2, h3 { color: var(--ink); letter-spacing: -0.035em; }
h1 { font-size: clamp(2.4rem, 5vw, 4.5rem) !important; line-height: .98 !important; margin-bottom: .65rem !important; }
h2 { margin-top: 2.3rem !important; font-size: 1.55rem !important; }
p { line-height: 1.65; }
.eyebrow { color: var(--accent); font-size: .78rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
.page-lead { color: var(--muted); max-width: 680px; font-size: 1.03rem; margin-bottom: 2rem; }
.quiet { color: var(--muted); font-size: .9rem; }
.section-rule { border-top: 1px solid var(--line); margin: 1.4rem 0 .25rem; }
.study-row, .course-row {
  border-top: 1px solid var(--line);
  padding: 1.05rem 0 .75rem;
  animation: rise .28s ease both;
}
.study-course { color: var(--accent); font-size: .78rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
.study-title { color: var(--ink); font-size: 1.12rem; font-weight: 650; margin-top: .18rem; }
.study-meta { color: var(--muted); font-size: .85rem; margin-top: .2rem; }
.progress-track { background: #e7e5df; border-radius: 999px; height: 7px; overflow: hidden; margin-top: .6rem; }
.progress-fill { background: var(--accent); height: 100%; border-radius: inherit; transition: width .5s ease; }
.status-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--success); margin-right: .45rem; }
.status-dot.planned { background: #98a2b3; }
.metric-number { font-size: 2rem; font-weight: 700; letter-spacing: -.04em; color: var(--ink); }
.metric-label { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }
.stButton > button {
  border-radius: 8px; border: 1px solid #cfd4df; font-weight: 650;
  transition: transform .14s ease, border-color .14s ease, background .14s ease;
}
.stButton > button:hover { transform: translateY(-1px); border-color: var(--accent); color: var(--accent); }
.stButton > button[kind="primary"] { background: var(--accent); color: white; border-color: var(--accent); }
[data-testid="stAlert"] { border-radius: 8px; }
@keyframes rise { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
