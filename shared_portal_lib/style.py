"""
Shared RTL layout, typography, and visual polish for every portal.
Colors and base theme come from .streamlit/config.toml - CSS here
handles direction, alignment, font, and the interactive/premium
polish: gradient login header with entrance animation, pill-style
radio choices, smoother hovers throughout.
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

.block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}

.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
    direction: rtl;
    text-align: right;
    font-size: 1rem;
    border-radius: 10px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    box-shadow: 0 0 0 2px rgba(59, 110, 143, 0.25);
}

.stButton button, .stDownloadButton button, .stFormSubmitButton button {
    border-radius: 10px;
    padding: 0.5rem 1.4rem;
    font-weight: 600;
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}
.stButton button:hover, .stDownloadButton button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(0,0,0,0.10);
}

div[data-testid="stExpander"] {
    border-radius: 12px;
    border: 1px solid rgba(0,0,0,0.08);
    transition: box-shadow 0.15s ease;
}
div[data-testid="stExpander"]:hover {
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
}

.stTabs [data-baseweb="tab"] {
    font-weight: 600;
    border-radius: 10px 10px 0 0;
}

/* Verdict choices (correct/incorrect radios) as interactive pills */
div[data-testid="stRadio"] > div {
    gap: 10px;
}
div[data-testid="stRadio"] label {
    background: #EFEAE2;
    padding: 10px 24px !important;
    border-radius: 999px;
    transition: all 0.15s ease;
    cursor: pointer;
    border: 2px solid transparent;
}
div[data-testid="stRadio"] label:hover {
    background: #E4DDD0;
    transform: translateY(-1px);
}
div[data-testid="stRadio"] label[data-checked="true"] {
    border: 2px solid #3B6E8F;
    background: #EAF2F6;
}

/* Login: gradient icon header with a soft entrance */
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}
.login-header {
    text-align: center;
    margin-top: 1.5rem;
    animation: fadeSlideIn 0.5s ease-out;
}
.login-icon {
    font-size: 2.8rem;
    margin-bottom: 0.4rem;
}
.login-title {
    font-size: 1.7rem;
    font-weight: 700;
    background: linear-gradient(90deg, #3B6E8F, #2E9E6B);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

div[data-testid="stForm"] {
    max-width: 480px;
    margin: 1.5rem auto 2rem auto;
    padding: 2.2rem;
    border-radius: 16px;
    box-shadow: 0 6px 24px rgba(0,0,0,0.08);
    border-top: 4px solid #3B6E8F;
    animation: fadeSlideIn 0.6s ease-out 0.1s both;
}
div[data-testid="stForm"] label {
    text-align: center !important;
    width: 100%;
}
div[data-testid="stForm"] input {
    text-align: center;
}
.stFormSubmitButton button {
    background: linear-gradient(90deg, #3B6E8F, #2E9E6B) !important;
    color: #ffffff !important;
    border: none !important;
}
.stFormSubmitButton button:hover {
    filter: brightness(1.08);
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(46, 158, 107, 0.3) !important;
}
</style>
"""


def apply_rtl_style() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def render_login_header(title: str, icon: str = "⚖️") -> None:
    st.markdown(
        f'<div class="login-header"><div class="login-icon">{icon}</div>'
        f'<div class="login-title">{title}</div></div>',
        unsafe_allow_html=True,
    )
