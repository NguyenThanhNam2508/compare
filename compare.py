import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Appo vs Xendit Reconciliation", layout="wide")
st.title("Appo vs Xendit Reconciliation Tool")

# ============================================================
# Helpers
# ============================================================


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

tab1, tab2, tab3 = st.tabs([
    "📊 APPO X XENDIT",
    "🔎 DIGISTORE X APPO",
    "💳 CHECK FEE MASTER MERCHANT"
])

# ============================================================
# TAB 1 - APPO X XENDIT
# ============================================================

with tab1:

    st.subheader("So sánh File A (Appo) và File B (Xendit)")

    col_upload_1, col_upload_2 = st.columns(2)

    with col_upload_1:
        f1 = st.file_uploader("FILE APPO (.xlsx)", type=["xlsx"], key="t1_f1")

    with col_upload_2:
        f2 = st.file_uploader("FILE XENDIT (.xlsx)",
                              type=["xlsx"], key="t1_f2")

    if f1 and f2:

        sheet_a = st.selectbox(
            "Sheet File APPO", get_sheet_names(f1), key="t1_s1")
        sheet_b = st.selectbox("Sheet File XENDIT",
                               get_sheet_names(f2), key="t1_s2")

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

            # ====================================================
            # MERGE XENDIT -> APPO (tính số liệu)
            # ====================================================

            merged_b_to_a = df_b_compare.merge(
                df_a_compare,
                on=common_cols,
                how="left",
                indicator=True
            )

            b_not_in_a = merged_b_to_a[merged_b_to_a["_merge"] == "left_only"]
            b_in_a_count = total_b - len(b_not_in_a)
            appo_after_minus = total_a - b_in_a_count
            # ================= THÔNG BÁO =================

            if len(b_not_in_a) > 0:
                st.error(
                    f"❌ Có {len(b_not_in_a)} giao dịch trong Xendit KHÔNG tồn tại trong Appo.")
            else:
                st.success("✅ Toàn bộ dữ liệu Xendit đều tồn tại trong Appo.")
            # ====================================================
            # MERGE APPO (để highlight)
            # ====================================================

            merged_appo = df_a_compare.merge(
                df_b_compare,
                on=common_cols,
                how="left",
                indicator=True
            )

            df_appo_full = merged_appo.copy()
            df_appo_full["Status"] = df_appo_full["_merge"].apply(
                lambda x: "Matched" if x == "both" else "Only in Appo"
            )

            df_appo_minus_xendit = df_appo_full[
                df_appo_full["Status"] == "Only in Appo"
            ].drop(columns=["_merge", "Status"])

            df_xendit_full = df_b.copy()

            # ====================================================
            # HIGHLIGHT FUNCTION
            # ====================================================

            def highlight_match(row):
                if row["Status"] == "Matched":
                    return ["background-color: #d4edda"] * len(row)
                return [""] * len(row)

            # ====================================================
            # UI RESULT
            # ====================================================

            st.markdown("## 📊 KẾT QUẢ")

            col1, col2, col3 = st.columns(3)
            col1.metric("Tổng giao dịch Appo", total_a)
            col2.metric("Tổng giao dịch Xendit", total_b)
            col3.metric("Appo sau khi trừ Xendit", appo_after_minus)

            st.markdown("---")

            # 1️⃣ APPO FULL + HIGHLIGHT
            st.markdown(
                "### 📄 File Appo (highlight giao dịch tồn tại trong Xendit)")

            df_show_appo = df_appo_full.drop(
                columns=["_merge"]).reset_index(drop=True)
            df_show_appo.index += 1

            st.dataframe(
                df_show_appo.style.apply(highlight_match, axis=1),
                use_container_width=True
            )

            # 2️⃣ XENDIT FULL
            st.markdown("### 📄 File Xendit (Full Data)")

            df_show_xendit = df_xendit_full.reset_index(drop=True)
            df_show_xendit.index += 1

            st.dataframe(df_show_xendit, use_container_width=True)

            # 3️⃣ APPO - XENDIT
            st.markdown("### 📄 Appo - Xendit (Chỉ có ở Appo)")

            df_minus = df_appo_minus_xendit.reset_index(drop=True)
            df_minus.index += 1

            st.dataframe(df_minus, use_container_width=True)

            # ====================================================
            # EXPORT
            # ====================================================

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_a.to_excel(writer, index=False, sheet_name="Appo")
                df_b.to_excel(writer, index=False, sheet_name="Xendit")
                b_not_in_a[common_cols].to_excel(
                    writer, index=False, sheet_name="Xendit_Not_In_Appo"
                )
                df_appo_minus_xendit.to_excel(
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
# TAB 2 - SO SÁNH LINH HOẠT + SHOW CỘT SONG SONG
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

            # Lấy cột chung (bỏ STT)
            common_cols = list(set(df_a.columns) & set(df_b.columns))
            common_cols = [c for c in common_cols if c.lower() != "stt"]

            if not common_cols:
                st.error("❌ Không có cột chung để so sánh.")
                st.stop()

            st.info(f"Các cột được dùng để so sánh: {common_cols}")

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

            # ================= KẾT QUẢ =================

            st.markdown("## 📊 KẾT QUẢ")

            col1, col2, col3 = st.columns(3)
            col1.metric("Tổng dòng File A", len(df_a_compare))
            col2.metric("Tổng dòng File B", len(df_b_compare))
            col3.metric("B không tồn tại trong A", len(b_not_in_a))

            if len(b_not_in_a) > 0:
                st.error("❌ Có dữ liệu File B không tồn tại trong File A.")
            else:
                st.success("✅ Tất cả dữ liệu File B tồn tại trong File A.")

            # =================================================
            # 🔎 HIỂN THỊ TỪNG CẶP CỘT SONG SONG (ĐÃ SORT)
            # =================================================

            st.markdown("---")
            st.subheader("🔎 So sánh từng cột giữa 2 file (đã sắp xếp)")

            for col in common_cols:

                st.markdown(f"### 📌 Cột: {col}")

                df_a_sorted = (
                    df_a_compare[[col]]
                    .sort_values(by=col)
                    .reset_index(drop=True)
                )

                df_b_sorted = (
                    df_b_compare[[col]]
                    .sort_values(by=col)
                    .reset_index(drop=True)
                )

                left, right = st.columns(2)

                with left:
                    st.markdown("**File A (đã sắp xếp)**")
                    st.dataframe(
                        df_a_sorted,
                        use_container_width=True,
                        height=400
                    )

                with right:
                    st.markdown("**File B (đã sắp xếp)**")
                    st.dataframe(
                        df_b_sorted,
                        use_container_width=True,
                        height=400
                    )

                st.markdown("---")

            # =================================================
            # SHOW PHẦN CHÊNH LỆCH
            # =================================================

            st.subheader("❗ Dữ liệu chỉ có trong File A")
            st.dataframe(a_not_in_b[common_cols], use_container_width=True)

            st.subheader("❗ Dữ liệu chỉ có trong File B")
            st.dataframe(b_not_in_a[common_cols], use_container_width=True)
# ============================================================
# TAB 3 - CHECK FEE MASTER MERCHANT (FINAL VERSION)
# ============================================================

with tab3:

    st.subheader("Kiểm tra Fee Master Merchant (Dynamic Rule)")

    # ================= RULE INPUT =================
    st.markdown("### 🔧 Nhập Rule Tính Fee")

    network_options = [
        "visa",
        "mastercard",
        "jcb",
        "unionpay",
        "amex",
        "napas"
    ]

    rule_data = st.data_editor(
        pd.DataFrame({
            "card_origin": pd.Series(dtype="int"),
            "network": pd.Series(dtype="str"),
            "fee_percent": pd.Series(dtype="float")
        }),
        column_config={
            "card_origin": st.column_config.SelectboxColumn(
                "Card Origin",
                options=[0, 1, 2],
                required=True
            ),
            "network": st.column_config.SelectboxColumn(
                "Network",
                options=network_options,
                required=True
            ),
            "fee_percent": st.column_config.NumberColumn(
                "Fee Percent (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.2f",
                required=True
            ),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="rule_editor"
    )

    st.markdown("---")

    # ================= UPLOAD FILE =================
    file_fee = st.file_uploader(
        "Upload File (.xlsx)",
        type=["xlsx"],
        key="t3_file"
    )

    if file_fee:

        sheet_fee = st.selectbox(
            "Chọn Sheet",
            get_sheet_names(file_fee),
            key="t3_sheet"
        )

        df_fee = read_excel(file_fee, sheet_name=sheet_fee)
        df_fee.columns = df_fee.columns.str.strip()

        required_cols = [
            "card_origin",
            "network",
            "amount",
            "fee_master_merchant_amount"
        ]

        if not all(col in df_fee.columns for col in required_cols):
            st.error("❌ File thiếu một trong các cột bắt buộc.")
            st.stop()

        if st.button("Kiểm tra Fee", type="primary", key="t3_compare"):

            if rule_data.empty:
                st.error("❌ Vui lòng nhập ít nhất 1 rule tính fee.")
                st.stop()

            df_calc = df_fee.copy()

            # ================= CLEAN FILE =================
            df_calc["card_origin"] = (
                pd.to_numeric(df_calc["card_origin"], errors="coerce")
                .fillna(-999)
                .astype(int)
            )

            df_calc["network"] = (
                df_calc["network"]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            df_calc["amount"] = pd.to_numeric(
                df_calc["amount"], errors="coerce"
            ).fillna(0)

            df_calc["fee_master_merchant_amount"] = pd.to_numeric(
                df_calc["fee_master_merchant_amount"], errors="coerce"
            ).fillna(0)

            # ================= CLEAN RULE =================
            rule_df = rule_data.copy()

            rule_df["card_origin"] = (
                pd.to_numeric(rule_df["card_origin"], errors="coerce")
                .fillna(-999)
                .astype(int)
            )

            rule_df["network"] = (
                rule_df["network"]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            rule_df["fee_percent"] = pd.to_numeric(
                rule_df["fee_percent"], errors="coerce"
            )

            # Remove duplicate rule (tránh nhân dòng khi merge)
            rule_df = rule_df.drop_duplicates(
                subset=["card_origin", "network"],
                keep="last"
            )

            # ================= MERGE =================
            df_merged = df_calc.merge(
                rule_df,
                on=["card_origin", "network"],
                how="left"
            )

            # ================= CALCULATE =================
            df_merged["Rule_Found"] = df_merged["fee_percent"].notna()

            df_merged["fee_calculated"] = (
                df_merged["amount"] *
                (df_merged["fee_percent"] / 100)
            )

            df_merged["fee_calculated"] = df_merged["fee_calculated"].fillna(0)

            df_merged["fee_diff"] = (
                df_merged["fee_master_merchant_amount"]
                - df_merged["fee_calculated"]
            )

            # ================= STATUS =================
            df_merged["Status"] = "Correct"

            df_merged.loc[
                ~df_merged["Rule_Found"],
                "Status"
            ] = "No Rule"

            df_merged.loc[
                (df_merged["Rule_Found"]) &
                (df_merged["fee_diff"].abs() >= 0.01),
                "Status"
            ] = "Mismatch"

            # ================= SUMMARY =================
            total = len(df_merged)
            mismatch_count = (df_merged["Status"] == "Mismatch").sum()
            no_rule_count = (df_merged["Status"] == "No Rule").sum()

            st.markdown("## 📊 KẾT QUẢ")

            col1, col2, col3 = st.columns(3)
            col1.metric("Tổng số dòng", total)
            col2.metric("Sai Fee", mismatch_count)
            col3.metric("Không tìm thấy Rule", no_rule_count)

            if mismatch_count > 0:
                st.error(f"❌ Có {mismatch_count} dòng tính sai fee.")
            elif no_rule_count > 0:
                st.warning(f"⚠ Có {no_rule_count} dòng không tìm thấy rule.")
            else:
                st.success("✅ Tất cả fee đều đúng.")

            # ================= HIGHLIGHT =================
            def highlight_fee(row):
                if row["Status"] == "Mismatch":
                    return ["background-color: #f8d7da"] * len(row)
                elif row["Status"] == "No Rule":
                    return ["background-color: #fff3cd"] * len(row)
                return [""] * len(row)

            df_show = df_merged.reset_index(drop=True)
            df_show.index += 1

            st.dataframe(
                df_show.style.apply(highlight_fee, axis=1),
                use_container_width=True
            )
