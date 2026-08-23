"""
RTL layout + Arabic typography for the Streamlit portal. Colors and
base theme come from .streamlit/config.toml (Streamlit's native
theming), not CSS overrides - CSS here only handles what the theme
system can't: text direction, alignment, font import, and sizing.
"""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif;
    font-size: 18px;
}

.stApp {
    direction: rtl;
}

.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp label, .stApp .stMarkdown, .stApp .stCaption, .stApp small {
    text-align: right;
}

.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
    direction: rtl;
    text-align: right;
    font-size: 1rem;
}

/* Login form: centered card - more specific than the rules above,
   so it wins without needing !important. */
div[data-testid="stForm"] {
    max-width: 480px;
    margin: 2rem auto;
    padding: 2rem;
    border-radius: 14px;
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
