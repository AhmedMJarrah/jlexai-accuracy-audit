"""
Volunteer portal for the law_meta audit pool. Login -> pick an
assigned record -> review reference values -> enter corrections ->
save. One standalone app per audit task, per project decision - this
app only ever touches the law_meta pool.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging
from step3_sampling.models import META_FIELDS, PoolName
from step4_sheets.client import open_spreadsheet
from step6_auth.authenticate import authenticate
from step7_updates.row_update import update_row
from shared_portal_lib.assignments import list_assigned, progress_summary
from shared_portal_lib.export import to_csv_bytes
from shared_portal_lib.style import apply_rtl_style, render_login_header

POOL = PoolName.LAW_META
STATUS_OPTIONS = ["not_started", "in_progress", "done", "flagged"]
STATUS_LABELS = {
    "not_started": "لم يبدأ",
    "in_progress": "قيد المراجعة",
    "done": "منتهي",
    "flagged": "بحاجة لمراجعة إضافية",
}
FIELD_LABELS = {
    "Leg_Number": "رقم التشريع",
    "Year": "السنة",
    "Status": "الحالة القانونية",
    "Magazine_Number": "رقم الجريدة الرسمية",
    "Magazine_Page": "الصفحة",
    "Magazine_Date": "تاريخ الجريدة الرسمية",
    "Issue_Date": "تاريخ الإصدار",
    "Active_Date": "تاريخ النفاذ",
    "End_Date": "تاريخ الانتهاء",
    "Replaced_By": "استُبدل بـ",
    "Replaced_For": "استُبدل عن",
    "Canceled_By": "أُلغي بموجب",
}


@st.cache_resource
def get_cached_spreadsheet():
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)
    return open_spreadsheet(settings)


def login_screen(settings) -> None:
    render_login_header("تدقيق البيانات الوصفية للتشريعات", icon="📋")
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


def review_form(spreadsheet, record: dict) -> bool:
    st.subheader(record["leg_name"])
    st.caption(f"رقم السجل: {record['record_id']}")

    header_l, header_r, header_c = st.columns([2, 3, 3])
    header_l.markdown("**الحقل**")
    header_r.markdown("**القيمة الحالية**")
    header_c.markdown("**التصحيح (اتركه فارغاً إذا كانت القيمة صحيحة)**")

    corrections: dict[str, str] = {}
    for field in META_FIELDS:
        ref_val = record.get(f"ref_{field}", "")
        existing_corr = record.get(f"corr_{field}", "")
        label = FIELD_LABELS.get(field, field)

        col_l, col_r, col_c = st.columns([2, 3, 3])
        col_l.markdown(label)
        col_r.text_input(
            "ref", value=ref_val, disabled=True,
            key=f"ref_{field}_{record['record_id']}", label_visibility="collapsed",
        )
        corrections[f"corr_{field}"] = col_c.text_input(
            "corr", value=existing_corr,
            key=f"corr_{field}_{record['record_id']}", label_visibility="collapsed",
        )

    notes = st.text_area(
        "ملاحظات", value=record.get("reviewer_notes", ""),
        key=f"notes_{record['record_id']}",
    )

    if st.button("حفظ", type="primary"):
        has_correction = any(v.strip() for v in corrections.values())
        status = "flagged" if has_correction else "done"
        try:
            update_row(spreadsheet, POOL, record["record_id"], corrections, status=status, notes=notes)
        except Exception as e:
            st.error("حدث خطأ أثناء الحفظ. حاول مرة أخرى.")
            st.exception(e)
            return False
        st.success("تم الحفظ بنجاح")
        return True
    return False


def main() -> None:
    st.set_page_config(page_title="تدقيق البيانات الوصفية", layout="wide")
    apply_rtl_style()

    settings = get_settings()
    spreadsheet = get_cached_spreadsheet()

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
            file_name=f"law_meta_{user.user_slot}.csv",
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
