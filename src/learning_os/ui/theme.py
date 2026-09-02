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
.block-container {
  max-width: 1120px; padding-top: 2.8rem; padding-bottom: 5rem;
  animation: page-in .24s ease both;
}
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
  transition: padding-left .16s ease, border-color .16s ease;
}
.study-row:hover, .course-row:hover { padding-left: .35rem; border-color: #cfd5e7; }
.study-course { color: var(--accent); font-size: .78rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
.study-title { color: var(--ink); font-size: 1.12rem; font-weight: 650; margin-top: .18rem; }
.study-meta { color: var(--muted); font-size: .85rem; margin-top: .2rem; }
.progress-track { background: #e7e5df; border-radius: 999px; height: 7px; overflow: hidden; margin-top: .6rem; }
.progress-fill { background: var(--accent); height: 100%; border-radius: inherit; transition: width .5s ease; }
.status-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--success); margin-right: .45rem; }
.status-dot.planned { background: #98a2b3; }
.metric-number { font-size: 2rem; font-weight: 700; letter-spacing: -.04em; color: var(--ink); }
.metric-label { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }
.glossary-inline {
  appearance: none;
  background: transparent;
  border: 0;
  border-bottom: 1px dotted var(--accent);
  color: var(--accent);
  cursor: help;
  display: inline;
  font: inherit;
  font-weight: 650;
  line-height: inherit;
  margin: 0 .06rem;
  padding: 0 .04rem;
  position: relative;
  text-align: inherit;
}
.glossary-inline:hover, .glossary-inline:focus-visible {
  background: var(--accent-soft);
  border-radius: 4px;
  outline: none;
}
.glossary-inline-card {
  background: #ffffff;
  border: 1px solid #d6dbea;
  border-radius: 10px;
  box-shadow: 0 12px 32px rgba(20, 33, 61, .16);
  color: var(--ink);
  cursor: default;
  display: none;
  font-size: .9rem;
  font-weight: 400;
  left: 0;
  line-height: 1.55;
  max-height: 280px;
  overflow-y: auto;
  padding: .9rem 1rem;
  position: absolute;
  text-align: left;
  top: calc(100% + .45rem);
  white-space: normal;
  width: min(360px, 78vw);
  z-index: 1000;
}
.glossary-inline-card strong, .glossary-inline-card span {
  display: block;
}
.glossary-inline-card strong {
  color: var(--accent);
  font-size: 1rem;
  margin-bottom: .35rem;
}
.glossary-inline-example {
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: .82rem;
  margin-top: .65rem;
  padding-top: .55rem;
}
.glossary-inline:hover .glossary-inline-card,
.glossary-inline:focus .glossary-inline-card,
.glossary-inline:focus-within .glossary-inline-card {
  display: block;
}
.lesson-markdown p, .lesson-markdown li { line-height: 1.7; }
.lesson-markdown table {
  border-collapse: collapse;
  display: block;
  margin: 1rem 0;
  max-width: 100%;
  overflow-x: auto;
  width: max-content;
}
.lesson-markdown th, .lesson-markdown td {
  border-bottom: 1px solid var(--line);
  padding: .55rem .75rem;
  text-align: left;
  vertical-align: top;
}
.lesson-markdown th { background: #f3f1ec; font-weight: 700; }
.lesson-markdown pre {
  background: #f3f1ec;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow-x: auto;
  padding: .9rem 1rem;
}
.lesson-markdown code {
  background: #f0eee9;
  border-radius: 4px;
  font-family: "Cascadia Code", Consolas, monospace;
  font-size: .88em;
  padding: .12rem .3rem;
}
.lesson-markdown pre code { background: transparent; padding: 0; }
.lesson-markdown blockquote {
  border-left: 3px solid #cfd5e7;
  color: var(--muted);
  margin-left: 0;
  padding-left: 1rem;
}
.stButton > button {
  border-radius: 8px; border: 1px solid #cfd4df; font-weight: 650;
  transition: transform .14s ease, border-color .14s ease, background .14s ease;
}
.stButton > button:hover { transform: translateY(-1px); border-color: var(--accent); color: var(--accent); }
.stButton > button[kind="primary"] { background: var(--accent); color: white; border-color: var(--accent); }
[data-testid="stAlert"] { border-radius: 8px; }
@keyframes rise { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
@keyframes page-in { from { opacity: .75; } to { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
