import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Appo vs Xendit Reconciliation", layout="wide")
st.title("Appo vs Xendit Reconciliation Tool")

# ---------------- Helpers ----------------


def read_excel(uploaded_file, sheet_name=None):
    df = pd.read_excel(uploaded_file, dtype=str, sheet_name=sheet_name)
    df = df.fillna("")
    return df


def normalize_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.lower()
    s = s.replace({"nan": "", "none": "", "nat": ""})
    return s


def get_sheet_names(xlsx_file):
    try:
        xl = pd.ExcelFile(xlsx_file)
        return xl.sheet_names
    except Exception:
        return ["Sheet1"]

# ============================================================
# TABS
# ============================================================


tab1, tab2 = st.tabs([
    "📊 APPO X XENDIT",
    "🔎 DIGISTORE X APPO"
])

# ============================================================
# TAB 1 - APPO X XENDIT
# ============================================================

with tab1:

    st.subheader("So sánh File A (Appo) và File B (Xendit)")

    c1, c2 = st.columns(2)
    with c1:
        f1 = st.file_uploader("FILE APPO (.xlsx)", type=["xlsx"], key="t1_f1")
    with c2:
        f2 = st.file_uploader("FILE XENDIT (.xlsx)",
                              type=["xlsx"], key="t1_f2")

    if f1 and f2:

        sheet_a = st.selectbox(
            "Sheet File A", get_sheet_names(f1), key="t1_s1")
        sheet_b = st.selectbox(
            "Sheet File B", get_sheet_names(f2), key="t1_s2")

        df_a = read_excel(f1, sheet_name=sheet_a)
        df_b = read_excel(f2, sheet_name=sheet_b)

        df_a.columns = df_a.columns.str.strip()
        df_b.columns = df_b.columns.str.strip()

        if st.button("Compare", type="primary", key="t1_compare"):

            common_cols = list(set(df_a.columns) & set(df_b.columns))
            common_cols = [c for c in common_cols if c.lower() != "stt"]

            if not common_cols:
                st.error("❌ Không có cột chung giữa 2 file.")
                st.stop()

            df_a_compare = df_a[common_cols].copy()
            df_b_compare = df_b[common_cols].copy()

            for col in common_cols:
                df_a_compare[col] = normalize_series(df_a_compare[col])
                df_b_compare[col] = normalize_series(df_b_compare[col])

            total_a = len(df_a_compare)
            total_b = len(df_b_compare)

            merged = df_b_compare.merge(
                df_a_compare,
                on=common_cols,
                how="left",
                indicator=True
            )

            b_not_in_a = merged[merged["_merge"] == "left_only"]
            b_in_a_count = total_b - len(b_not_in_a)
            appo_after_minus = total_a - b_in_a_count

            # ===== UI RESULT =====

            st.markdown("## 📊 KẾT QUẢ")

            col1, col2, col3 = st.columns(3)
            col1.metric("Tổng giao dịch Appo", total_a)
            col2.metric("Tổng giao dịch Xendit", total_b)
            col3.metric("Appo sau khi trừ Xendit", appo_after_minus)

            if len(b_not_in_a) > 0:
                st.error("❌ Có dữ liệu Xendit KHÔNG tồn tại trong Appo.")
                st.dataframe(b_not_in_a[common_cols], use_container_width=True)
            else:
                st.success("✅ Toàn bộ dữ liệu Xendit tồn tại trong Appo.")

            # ===== DATA DETAIL =====

            st.markdown("---")
            st.markdown("## 📄 DỮ LIỆU CHI TIẾT")

            with st.expander("📂 File APPO (cột so sánh)"):
                st.dataframe(df_a_compare, use_container_width=True)

            with st.expander("📂 File XENDIT (cột so sánh)"):
                st.dataframe(df_b_compare, use_container_width=True)

            # Appo - Xendit
            merged_reverse = df_a_compare.merge(
                df_b_compare,
                on=common_cols,
                how="left",
                indicator=True
            )

            a_not_in_b = merged_reverse[merged_reverse["_merge"]
                                        == "left_only"]

            with st.expander("📂 APPO sau khi trừ XENDIT"):
                st.dataframe(a_not_in_b[common_cols], use_container_width=True)

            # ===== EXPORT =====

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_a.to_excel(writer, index=False, sheet_name="Appo")
                df_b.to_excel(writer, index=False, sheet_name="Xendit")
                b_not_in_a[common_cols].to_excel(
                    writer, index=False, sheet_name="Xendit_Not_In_Appo"
                )
                a_not_in_b[common_cols].to_excel(
                    writer, index=False, sheet_name="Appo_Not_In_Xendit"
                )

            output.seek(0)

            st.download_button(
                "Download Report Excel",
                data=output,
                file_name="appo_vs_xendit_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# ============================================================
# TAB 2 - DIGISTORE X APPO
# ============================================================

with tab2:

    st.subheader("So sánh linh hoạt - Tự động lấy cột giống nhau")

    c1, c2 = st.columns(2)
    with c1:
        f1 = st.file_uploader("Upload File A (.xlsx)",
                              type=["xlsx"], key="t2_f1")
    with c2:
        f2 = st.file_uploader("Upload File B (.xlsx)",
                              type=["xlsx"], key="t2_f2")

    if f1 and f2:

        sheet_a = st.selectbox(
            "Sheet File A", get_sheet_names(f1), key="t2_s1")
        sheet_b = st.selectbox(
            "Sheet File B", get_sheet_names(f2), key="t2_s2")

        df_a = read_excel(f1, sheet_name=sheet_a)
        df_b = read_excel(f2, sheet_name=sheet_b)

        df_a.columns = df_a.columns.str.strip()
        df_b.columns = df_b.columns.str.strip()

        if st.button("Compare Linh Hoạt", type="primary", key="t2_compare"):

            common_cols = list(set(df_a.columns) & set(df_b.columns))
            common_cols = [c for c in common_cols if c.lower() != "stt"]

            if not common_cols:
                st.error("❌ Không có cột chung để so sánh.")
                st.stop()

            df_a_compare = df_a[common_cols].copy()
            df_b_compare = df_b[common_cols].copy()

            for col in common_cols:
                df_a_compare[col] = normalize_series(df_a_compare[col])
                df_b_compare[col] = normalize_series(df_b_compare[col])

            merged = df_b_compare.merge(
                df_a_compare,
                on=common_cols,
                how="outer",
                indicator=True
            )

            b_not_in_a = merged[merged["_merge"] == "left_only"]
            a_not_in_b = merged[merged["_merge"] == "right_only"]

            st.markdown("## 📊 KẾT QUẢ")

            col1, col2 = st.columns(2)
            col1.metric("Tổng dòng File A", len(df_a_compare))
            col2.metric("Tổng dòng File B", len(df_b_compare))

            st.metric("B không tồn tại trong A", len(b_not_in_a))

            st.markdown("---")
            st.subheader("📄 Data File A")
            st.dataframe(df_a_compare, use_container_width=True)

            st.subheader("📄 Data File B")
            st.dataframe(df_b_compare, use_container_width=True)

            st.subheader("❗ Chỉ có trong File A")
            st.dataframe(a_not_in_b[common_cols], use_container_width=True)

            st.subheader("❗ Chỉ có trong File B")
            st.dataframe(b_not_in_a[common_cols], use_container_width=True)
