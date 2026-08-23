"""
Additional CSS specific to the chain portal's timeline visualization,
layered on top of the shared RTL/theme styling. Numbered badges on a
gradient spine, colored status pills, subtle card elevation.
"""
import streamlit as st

from shared_portal_lib.style import apply_rtl_style

_TIMELINE_CSS = """
<style>
.chain-timeline {
    position: relative;
    padding-right: 44px;
    margin: 1.5rem 0;
}
.chain-timeline::before {
    content: "";
    position: absolute;
    right: 14px;
    top: 4px;
    bottom: 4px;
    width: 3px;
    background: linear-gradient(180deg, #3B6E8F, #A9C8D6);
    border-radius: 3px;
}
.chain-node {
    position: relative;
    margin-bottom: 1.4rem;
    padding: 1rem 1.2rem;
    border-radius: 14px;
    background: #ffffff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    transition: transform 0.15s ease;
}
.chain-node:hover {
    transform: translateX(-4px);
}
.chain-node::before {
    content: attr(data-num);
    position: absolute;
    right: -44px;
    top: 50%;
    transform: translateY(-50%);
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #3B6E8F;
    color: #ffffff;
    font-weight: 700;
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    justify-content: center;
}
.chain-base {
    border: 2px solid #3B6E8F;
    background: #EAF2F6;
}
.chain-base::before {
    background: #2F5A75;
}
.chain-badge {
    font-size: 0.78rem;
    color: #3B6E8F;
    font-weight: 700;
    letter-spacing: 0.3px;
}
.chain-name {
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0.25rem 0;
    color: #262626;
}
.chain-meta {
    font-size: 0.9rem;
    color: #666;
}
.chain-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-inline-start: 8px;
}
.chain-pill-active {
    background: #DCF3E4;
    color: #1E7B45;
}
.chain-pill-inactive {
    background: #FBE4E4;
    color: #A33A3A;
}
.chain-pill-neutral {
    background: #EFEAE2;
    color: #555555;
}
</style>
"""


def apply_chain_style() -> None:
    apply_rtl_style()
    st.markdown(_TIMELINE_CSS, unsafe_allow_html=True)
