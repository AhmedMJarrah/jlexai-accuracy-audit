"""
Admin portal: progress overview across all pools, work reassignment,
volunteer identity management, and releasing full-population batches
beyond the initial 100-sample. Admin-only login - same credentials
as the volunteer portals, but is_admin must be true.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging
from step2_ingestion.adapters import get_adapter
from step2_ingestion.models import LegType
from step3_sampling.models import LegKind, PoolName
from step4_sheets.client import open_spreadsheets_for_settings, spreadsheet_for_pool
from step4_sheets.sync import append_batch
from step5_release.service import create_batch
from step6_auth.authenticate import authenticate
from step6_auth.users_config import load_users
from step9_admin_portal.progress import all_pools_progress
from step9_admin_portal.reassign import reassign_not_started
from step9_admin_portal.users_admin import update_volunteer
from shared_portal_lib.style import apply_rtl_style, render_login_header


@st.cache_resource
def get_cached_spreadsheets():
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)
    return open_spreadsheets_for_settings(settings)


def login_screen(settings) -> None:
    render_login_header("لوحة تحكم المشرف", icon="🛠️")
    with st.form("admin_login_form"):
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
    elif not user.is_admin:
        st.warning("هذا الحساب متطوع - الرجاء استخدام بوابة التدقيق الخاصة به")
    else:
        st.session_state["admin"] = user
        st.rerun()


def _finished_fraction(counts: dict) -> tuple[int, float]:
    """"Finished" = done + flagged - both mean the volunteer actually
    completed their review, flagged just also notes a concern."""
    total = counts.get("total", 0)
    finished = counts.get("done", 0) + counts.get("flagged", 0)
    return finished, (finished / total if total else 0.0)


def progress_tab(spreadsheets) -> None:
    st.subheader("نظرة عامة على التقدم")
    reports = all_pools_progress(spreadsheets)

    for r in reports:
        if r["total"] == 0:
            st.caption(f"{r['pool']}: لم تتم مزامنته بعد")
            continue

        sc = r["status_counts"]
        sc["total"] = r["total"]
        finished, fraction = _finished_fraction(sc)

        st.write(f"**{r['pool']}** — {r['total']} سجل")
        st.progress(fraction, text=f"{finished} من {r['total']} منتهي ({fraction:.0%})")

        with st.expander("تفاصيل حسب المستخدم"):
            st.caption(
                f"لم يبدأ: {sc['not_started']} | قيد المراجعة: {sc['in_progress']} | "
                f"منتهي: {sc['done']} | بحاجة لمراجعة إضافية: {sc['flagged']}"
            )
            for user_slot, counts in sorted(r["per_user"].items()):
                user_finished, user_fraction = _finished_fraction(counts)
                st.write(f"{user_slot} — {user_finished} من {counts['total']} ({user_fraction:.0%})")
                st.progress(user_fraction)


def reassign_tab(spreadsheets, settings) -> None:
    st.subheader("إعادة توزيع العمل")
    st.caption("يتم نقل السجلات التي لم تبدأ بعد فقط - العمل الجاري أو المنتهي لا يُنقل.")

    pool = st.selectbox("نوع التدقيق", [p.value for p in PoolName], key="reassign_pool")
    slots = [f"user_slot_{i}" for i in range(1, settings.num_users + 1)]
    from_slot = st.selectbox("من المستخدم", slots, key="from_slot")
    to_slot = st.selectbox("إلى المستخدم", [s for s in slots if s != from_slot], key="to_slot")
    count = st.number_input("عدد السجلات", min_value=1, value=5, step=1)

    if st.button("نقل السجلات"):
        try:
            spreadsheet = spreadsheet_for_pool(PoolName(pool), spreadsheets)
            moved = reassign_not_started(spreadsheet, PoolName(pool), from_slot, to_slot, int(count))
        except Exception as e:
            st.error("حدث خطأ أثناء إعادة التوزيع - قد يكون هذا الجدول غير متاح بعد.")
            st.exception(e)
            return

        if moved:
            st.success(f"تم نقل {len(moved)} سجل من {from_slot} إلى {to_slot}")
        else:
            st.warning(f"لا توجد سجلات لم تبدأ بعد لدى {from_slot} في هذا الجدول")


def release_tab(spreadsheets, settings) -> None:
    st.subheader("توزيع باقي البيانات")
    st.caption(
        "بعد اكتمال عينة الـ100 الأولى، استخدم هذا القسم لإطلاق دفعات إضافية. "
        "ارفع ملف بيانات القوانين الحالي في كل مرة - هذا يضمن استخدام النسخة "
        "الصحيحة من البيانات دائماً، بدل الاعتماد على ملف محفوظ قد يصبح قديماً."
    )

    uploaded = st.file_uploader("ملف بيانات القوانين (JSON)", type="json", key="release_upload")
    if uploaded is None:
        st.info("ارفع ملف JSON للمتابعة.")
        return

    law_pools = [p.value for p in PoolName if PoolName(p.value).leg_kind == LegKind.LAW]
    pool = st.selectbox("نوع التدقيق", law_pools, key="release_pool")
    slots = [f"user_slot_{i}" for i in range(1, settings.num_users + 1)]
    user_slot = st.selectbox("المستخدم", slots, key="release_user")
    count = st.number_input("عدد السجلات للإطلاق", min_value=1, value=50, step=10)
    note = st.text_input("ملاحظة (اختياري)", key="release_note")

    if st.button("إطلاق الدفعة"):
        try:
            spreadsheet = spreadsheet_for_pool(PoolName(pool), spreadsheets)
            records = get_adapter(LegType.LAW).load_from_text(uploaded.getvalue().decode("utf-8"))
            batch = create_batch(PoolName(pool), user_slot, int(count), records, spreadsheet, settings, note)
        except Exception as e:
            st.error("حدث خطأ أثناء إنشاء الدفعة.")
            st.exception(e)
            return

        if batch is None:
            st.warning(f"لا توجد سجلات متبقية في '{pool}' لإطلاقها - تم إسناد كامل البيانات بالفعل.")
            return

        try:
            append_batch(spreadsheet, batch)
        except Exception as e:
            st.error(f"فشل رفع الدفعة إلى الشيت: {e}. لم يُكتب شيء بعد - يمكنك المحاولة مجدداً بأمان.")
            st.exception(e)
            return

        st.success(f"تم إطلاق {len(batch.records)} سجل من '{pool}' إلى {user_slot}")


def volunteers_tab(settings) -> None:
    st.subheader("إدارة المتطوعين")
    st.caption(
        "عدد المستخدمين ثابت بحسب التوزيع الأصلي للعينة - "
        "هذا القسم يعدّل الاسم المرتبط بكل فتحة، ولا يضيف فتحات جديدة."
    )

    users = load_users(settings.users_config_file)
    for u in users:
        if u.user_slot is None:
            continue
        with st.form(f"edit_{u.user_slot}"):
            st.write(f"**{u.user_slot}**")
            new_username = st.text_input("اسم المستخدم", value=u.username, key=f"username_{u.user_slot}")
            new_display = st.text_input("الاسم المعروض", value=u.display_name, key=f"display_{u.user_slot}")
            if st.form_submit_button("حفظ"):
                update_volunteer(settings.users_config_file, u.user_slot, new_username, new_display)
                st.success("تم الحفظ - أعد تحميل الصفحة لرؤية التغيير")


def main() -> None:
    st.set_page_config(page_title="لوحة تحكم المشرف", layout="wide")
    apply_rtl_style()

    settings = get_settings()

    if "admin" not in st.session_state:
        login_screen(settings)
        return

    admin = st.session_state["admin"]
    st.sidebar.write(f"مرحباً، {admin.display_name or admin.username}")
    if st.sidebar.button("تسجيل الخروج"):
        del st.session_state["admin"]
        st.rerun()

    spreadsheets = get_cached_spreadsheets()

    tab1, tab2, tab3, tab4 = st.tabs(["التقدم", "إعادة التوزيع", "توزيع باقي البيانات", "المتطوعون"])
    with tab1:
        progress_tab(spreadsheets)
    with tab2:
        reassign_tab(spreadsheets, settings)
    with tab3:
        release_tab(spreadsheets, settings)
    with tab4:
        volunteers_tab(settings)


if __name__ == "__main__":
    main()
