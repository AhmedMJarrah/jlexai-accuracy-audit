"""
Shared RTL layout, typography, and visual polish for every portal.
Colors and base theme come from .streamlit/config.toml (Streamlit's
native theming) - CSS here handles direction, alignment, font, and
the "comfortable, smooth, pleasant" polish pass: spacing, rounded
cards, gentle transitions, clearer buttons.
"""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif;
    font-size: 18px;
    line-height: 1.7;
}

.stApp {
    direction: rtl;
}

.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp label, .stApp .stMarkdown, .stApp .stCaption, .stApp small {
    text-align: right;
}

.stApp h1 { font-weight: 700; }
.stApp h2, .stApp h3 { font-weight: 600; }

/* Breathing room between blocks */
.block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}

/* Inputs: comfortable size, rounded, subtle border */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
    direction: rtl;
    text-align: right;
    font-size: 1rem;
    border-radius: 10px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    box-shadow: 0 0 0 2px rgba(59, 110, 143, 0.25);
}

/* Buttons: rounder, gentle hover lift */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {
    border-radius: 10px;
    padding: 0.5rem 1.4rem;
    font-weight: 600;
    transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.stButton button:hover, .stDownloadButton button:hover, .stFormSubmitButton button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(0,0,0,0.10);
}

/* Expanders and containers: soft card feel */
div[data-testid="stExpander"] {
    border-radius: 12px;
    border: 1px solid rgba(0,0,0,0.08);
}

/* Tabs: clearer active state */
.stTabs [data-baseweb="tab"] {
    font-weight: 600;
    border-radius: 10px 10px 0 0;
}

/* Login form: centered card - more specific than the rules above,
   so it wins without needing !important. */
div[data-testid="stForm"] {
    max-width: 480px;
    margin: 2rem auto;
    padding: 2.2rem;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
div[data-testid="stForm"] label {
    text-align: center !important;
    width: 100%;
}
div[data-testid="stForm"] input {
    text-align: center;
}
</style>
"""


def apply_rtl_style() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
