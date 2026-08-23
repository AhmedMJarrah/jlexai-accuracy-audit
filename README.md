# JLexAI Accuracy Audit — Google Sheets / Streamlit auditing system

Volunteer auditing tool covering metadata, chain, and reflection
checks for laws and bylaws, feeding a 600-sample data accuracy report.

## Setup
1. `python -m venv audit` (if not already created) and activate it
2. `pip install -r requirements.txt`
3. `copy .env.example .env` and adjust values
4. `python -m step1_scaffold.environment_doctor`

## Structure
One subfolder per build step (`step1_scaffold`, `step2_ingestion`, ...).
Config and logging are centralized in `step1_scaffold` and imported
by every later step — no hardcoded values elsewhere.