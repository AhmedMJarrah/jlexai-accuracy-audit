"""
Article-level visual styling for the reflection portal, layered on
top of the shared RTL style. The instruction text and the resulting
reflected text each get their own tinted "zone", and every article
inside is its own card - replacing what used to be one long
undifferentiated wall of text with something scannable.
"""
import streamlit as st

from shared_portal_lib.style import apply_rtl_style

_REFLECT_CSS = """
<style>
.reflect-zone {
    border-radius: 14px;
    padding: 1rem 1.2rem 1.2rem 1.2rem;
    margin-bottom: 1.2rem;
}
.zone-instruction { background: #EAF2F6; }
.zone-reflected { background: #EAF7F0; }

.reflect-section-title {
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 0.8rem;
}

.article-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.7rem;
    box-shadow: 0 1px 5px rgba(0,0,0,0.05);
    line-height: 1.95;
}
.article-instruction { border-right: 4px solid #3B6E8F; }
.article-reflected { border-right: 4px solid #2E9E6B; }

.article-number {
    display: inline-block;
    background: #EFEAE2;
    color: #444;
    font-size: 0.78rem;
    font-weight: 700;
    padding: 2px 10px;
    border-radius: 999px;
    margin-bottom: 0.4rem;
}
.article-title {
    font-weight: 700;
    font-size: 1rem;
    margin-bottom: 0.3rem;
    color: #222;
}
.article-text {
    color: #333;
    font-size: 0.98rem;
}
.empty-note {
    color: #888;
    font-style: italic;
    padding: 0.4rem 0;
}
</style>
"""


def apply_reflect_style() -> None:
    apply_rtl_style()
    st.markdown(_REFLECT_CSS, unsafe_allow_html=True)
