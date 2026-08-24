"""
Volunteer portal for the law_chain audit pool. Login -> pick an
assigned record -> see the amendment chain as a timeline -> judge
whether it's correct, with a note. Standalone app, touches only the
law_chain pool.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import streamlit as st

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging
from step3_sampling.models import PoolName
from step4_sheets.client import open_spreadsheet
from step6_auth.authenticate import authenticate
from step7_updates.row_update import update_row
from step10_law_chain_portal.style import apply_chain_style
from shared_portal_lib.style import render_login_header
from shared_portal_lib.assignments import list_assigned, progress_summary
from shared_portal_lib.export import to_csv_bytes

POOL = PoolName.LAW_CHAIN
STATUS_OPTIONS = ["not_started", "in_progress", "done", "flagged"]
STATUS_LABELS = {
    "not_started": "لم يبدأ",
    "in_progress": "قيد المراجعة",
    "done": "منتهي",
    "flagged": "بحاجة لمراجعة إضافية",
}
CHAIN_CHOICES = ["correct", "incorrect"]
CHAIN_LABELS = {"correct": "السلسلة صحيحة", "incorrect": "السلسلة غير صحيحة"}


@st.cache_resource
def get_cached_spreadsheet():
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)
    return open_spreadsheet(settings)


def login_screen(settings) -> None:
    render_login_header("تدقيق سلاسل التعديلات", icon="🔗")
    with st.form("login_form"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        submitted = st.form_submit_button("تسجيل الدخول", use_container_width=True)

    if not submitted:
        return

    try:
        user = authenticate(username, password, settings)
    except ValueError as e:
        st.error(f"خطأ في إعدادات النظام: {e}")
        return

    if user is None:
        st.error("اسم المستخدم أو كلمة المرور غير صحيحة")
    elif user.is_admin:
        st.warning("حسابات المشرفين تستخدم لوحة تحكم منفصلة (قيد الإنشاء) - الرجاء استخدام حساب متطوع هنا")
    else:
        st.session_state["user"] = user
        st.rerun()


def record_picker(assigned: list[dict]) -> dict | None:
    st.subheader("السجلات المُسندة إليك")
    summary = progress_summary(assigned)
    st.caption(
        f"الإجمالي: {summary['total']} | لم يبدأ: {summary['not_started']} | "
        f"قيد المراجعة: {summary['in_progress']} | منتهي: {summary['done']} | "
        f"بحاجة لمراجعة إضافية: {summary['flagged']}"
    )

    if not assigned:
        st.info("لا توجد سجلات مُسندة إليك في هذا الجدول حالياً.")
        return None

    if "current_index" not in st.session_state or st.session_state["current_index"] >= len(assigned):
        st.session_state["current_index"] = 0

    labels = [
        f"{r['leg_name']} ({r['record_id']}) — {STATUS_LABELS.get(r['status'], r['status'])}"
        for r in assigned
    ]
    chosen_index = st.selectbox(
        "اختر سجلاً للمراجعة",
        options=list(range(len(assigned))),
        index=st.session_state["current_index"],
        format_func=lambda i: labels[i],
    )
    st.session_state["current_index"] = chosen_index
    return assigned[chosen_index]


def _status_pill(status: str) -> str:
    if not status:
        return ""
    if "غير" in status:
        cls = "chain-pill-inactive"
    elif status.strip() == "ساري":
        cls = "chain-pill-active"
    else:
        cls = "chain-pill-neutral"
    return f'<span class="chain-pill {cls}">{status}</span>'


def render_timeline(chain_data: list[dict]) -> None:
    if not chain_data:
        st.info("لا توجد بيانات سلسلة لعرضها.")
        return

    html = ['<div class="chain-timeline">']
    amendment_num = 0
    for item in chain_data:
        is_base = item.get("kind") == "base"
        if is_base:
            badge = "التشريع الأساسي"
            data_num = "★"
        else:
            amendment_num += 1
            badge = f"تعديل رقم {amendment_num}"
            data_num = str(amendment_num)

        year = item.get("year") or "—"
        pill = _status_pill(item.get("status", ""))

        html.append(
            f'<div class="chain-node {"chain-base" if is_base else ""}" data-num="{data_num}">'
            f'<div class="chain-badge">{badge}</div>'
            f'<div class="chain-name">{item.get("leg_name", "")}</div>'
            f'<div class="chain-meta">السنة: {year}{pill}</div>'
            f'</div>'
        )
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def review_form(spreadsheet, record: dict) -> bool:
    st.subheader(record["leg_name"])
    st.caption(f"رقم السجل: {record['record_id']}")

    try:
        chain_data = json.loads(record.get("chain_data_json") or "[]")
    except json.JSONDecodeError:
        chain_data = []
        st.error("تعذّرت قراءة بيانات السلسلة لهذا السجل.")

    render_timeline(chain_data)

    existing_choice = record.get("chain_correct") or None
    chain_correct = st.radio(
        "هل هذه السلسلة صحيحة؟",
        CHAIN_CHOICES,
        index=CHAIN_CHOICES.index(existing_choice) if existing_choice in CHAIN_CHOICES else None,
        format_func=lambda v: CHAIN_LABELS[v],
        horizontal=True,
    )
    if st.button("حفظ", type="primary"):
        if chain_correct is None:
            st.warning("الرجاء تحديد ما إذا كانت السلسلة صحيحة قبل الحفظ.")
            return False
        status = "flagged" if chain_correct == "incorrect" else "done"
        try:
            update_row(spreadsheet, POOL, record["record_id"], {"chain_correct": chain_correct}, status=status)
        except Exception as e:
            st.error("حدث خطأ أثناء الحفظ. حاول مرة أخرى.")
            st.exception(e)
            return False
        st.success("تم الحفظ بنجاح")
        return True
    return False


def main() -> None:
    st.set_page_config(page_title="تدقيق سلاسل التعديلات", layout="wide")
    apply_chain_style()

    spreadsheet = get_cached_spreadsheet()
    settings = get_settings()

    if "user" not in st.session_state:
        login_screen(settings)
        return

    user = st.session_state["user"]
    st.sidebar.write(f"مرحباً، {user.display_name or user.username}")
    if st.sidebar.button("تسجيل الخروج"):
        del st.session_state["user"]
        st.rerun()

    assigned = list_assigned(spreadsheet, POOL, user.user_slot)
    if assigned:
        st.sidebar.download_button(
            "تنزيل نسخة CSV من عملي",
            data=to_csv_bytes(assigned),
            file_name=f"law_chain_{user.user_slot}.csv",
            mime="text/csv",
        )

    record = record_picker(assigned)
    if record:
        if review_form(spreadsheet, record):
            idx = st.session_state.get("current_index", 0)
            if idx + 1 < len(assigned):
                st.session_state["current_index"] = idx + 1
            st.rerun()


if __name__ == "__main__":
    main()
