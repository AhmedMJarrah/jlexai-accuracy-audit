"""
Volunteer portal for the law_reflect audit pool. Login -> pick an
assigned amended law -> review each amendment's instruction text
against the resulting consolidated text -> judge whether the whole
amendment sequence was correctly reflected, with a note. Standalone
app, touches only the law_reflect pool - and specifically the
dedicated reflect spreadsheet, not the main one.
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
from shared_portal_lib.assignments import list_assigned, progress_summary
from shared_portal_lib.export import to_csv_bytes
from step11_law_reflect_portal.style import apply_reflect_style

POOL = PoolName.LAW_REFLECT
STATUS_OPTIONS = ["not_started", "in_progress", "done", "flagged"]
STATUS_LABELS = {
    "not_started": "لم يبدأ",
    "in_progress": "قيد المراجعة",
    "done": "منتهي",
    "flagged": "بحاجة لمراجعة إضافية",
}
REFLECT_CHOICES = ["correct", "incorrect"]
REFLECT_LABELS = {"correct": "الانعكاس صحيح", "incorrect": "الانعكاس غير صحيح"}


@st.cache_resource
def get_cached_spreadsheet():
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)
    if not settings.google_reflect_spreadsheet_id:
        raise ValueError("GOOGLE_REFLECT_SPREADSHEET_ID is not set")
    return open_spreadsheet(settings, settings.google_reflect_spreadsheet_id)


def login_screen(settings) -> None:
    st.markdown(
        "<h1 style='text-align:center;'>تدقيق انعكاس التعديلات</h1>",
        unsafe_allow_html=True,
    )
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


def _article_card_html(article: dict, css_class: str) -> str:
    number = article.get("number") or ""
    title = article.get("title") or ""
    text = article.get("text") or "—"
    badge = f'<span class="article-number">{number}</span>' if number else ""
    title_html = f'<div class="article-title">{title}</div>' if title else ""
    return f'<div class="article-card {css_class}">{badge}{title_html}<div class="article-text">{text}</div></div>'


def _render_zone(title_text: str, articles: list[dict], zone_class: str, card_class: str) -> str:
    if not articles:
        cards_html = '<div class="empty-note">لا يوجد نص لهذا القسم.</div>'
    else:
        cards_html = "".join(_article_card_html(a, card_class) for a in articles)
    return (
        f'<div class="reflect-zone {zone_class}">'
        f'<div class="reflect-section-title">{title_text}</div>'
        f'{cards_html}</div>'
    )


def render_amendment(mod: dict) -> None:
    instruction_html = _render_zone(
        "📝 نص التعليمة (التعديل)",
        mod.get("instruction_articles") or [],
        "zone-instruction",
        "article-instruction",
    )
    reflected_html = _render_zone(
        "✅ النص بعد التطبيق (الانعكاس)",
        mod.get("reflected_articles") or [],
        "zone-reflected",
        "article-reflected",
    )
    st.markdown(instruction_html, unsafe_allow_html=True)
    st.markdown(reflected_html, unsafe_allow_html=True)


def render_reflections(mod_legs: list[dict]) -> None:
    if not mod_legs:
        st.info("لا توجد تعديلات لعرضها.")
        return

    amendment_num = 0
    for item in mod_legs:
        name = item.get("amendment_name", "")
        if name.startswith("⚠️"):
            st.warning(name)
            continue

        amendment_num += 1
        title = f"🗂️ تعديل {amendment_num}: {name} ({item.get('amendment_year') or '—'})"
        with st.expander(title, expanded=(amendment_num == 1)):
            render_amendment(item)


def review_form(spreadsheet, record: dict) -> bool:
    st.subheader(record["leg_name"])
    st.caption(f"رقم السجل: {record['record_id']}")

    try:
        mod_legs = json.loads(record.get("mod_legs_json") or "[]")
    except json.JSONDecodeError:
        mod_legs = []
        st.error("تعذّرت قراءة بيانات التعديلات لهذا السجل.")

    render_reflections(mod_legs)

    existing_choice = record.get("reflection_correct") or None
    reflection_correct = st.radio(
        "هل انعكست كل التعديلات بشكل صحيح؟",
        REFLECT_CHOICES,
        index=REFLECT_CHOICES.index(existing_choice) if existing_choice in REFLECT_CHOICES else None,
        format_func=lambda v: REFLECT_LABELS[v],
        horizontal=True,
    )
    status = st.selectbox(
        "حالة المراجعة",
        STATUS_OPTIONS,
        index=STATUS_OPTIONS.index(record.get("status") or "not_started"),
        format_func=lambda s: STATUS_LABELS[s],
    )

    if st.button("حفظ", type="primary"):
        field_updates = {}
        if reflection_correct is not None:
            field_updates["reflection_correct"] = reflection_correct
        try:
            update_row(spreadsheet, POOL, record["record_id"], field_updates, status=status)
        except Exception as e:
            st.error("حدث خطأ أثناء الحفظ. حاول مرة أخرى.")
            st.exception(e)
            return False
        st.success("تم الحفظ بنجاح")
        return True
    return False


def main() -> None:
    st.set_page_config(page_title="تدقيق انعكاس التعديلات", layout="wide")
    apply_reflect_style()

    settings = get_settings()

    try:
        spreadsheet = get_cached_spreadsheet()
    except Exception as e:
        st.error("تعذّر الاتصال بشيت الانعكاس - تأكد من إعداد GOOGLE_REFLECT_SPREADSHEET_ID.")
        st.exception(e)
        return

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
            file_name=f"law_reflect_{user.user_slot}.csv",
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
