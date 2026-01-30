import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Excel Column Comparator", layout="wide")
st.title("So sánh dữ liệu theo cột giữa 2 file Excel")

# ---------------- Helpers ----------------


def make_unique_columns(cols):
    seen = {}
    out = []
    for c in cols:
        c = str(c).strip()
        if c not in seen:
            seen[c] = 0
            out.append(c)
        else:
            seen[c] += 1
            out.append(f"{c}__dup{seen[c]}")
    return out


def read_excel(uploaded_file):
    df = pd.read_excel(uploaded_file, dtype=str).fillna("")
    df.columns = make_unique_columns(df.columns)
    return df


def normalize_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.lower()
    s = s.replace({"nan": "", "none": "", "nat": ""})
    return s


def to_df(values, colname="value"):
    return pd.DataFrame({colname: values})


# ---------------- UI ----------------
c1, c2 = st.columns(2)
with c1:
    f1 = st.file_uploader("Upload File A (.xlsx)", type=["xlsx"])
with c2:
    f2 = st.file_uploader("Upload File B (.xlsx)", type=["xlsx"])

if not f1 or not f2:
    st.stop()

df_a = read_excel(f1)
df_b = read_excel(f2)

st.subheader("Chọn cột để so sánh")
col1, col2 = st.columns(2)
with col1:
    col_a = st.selectbox("Cột ở File A", df_a.columns)
with col2:
    col_b = st.selectbox("Cột ở File B", df_b.columns)

# ---------------- Compare ----------------
if st.button("Compare", type="primary"):
    a = normalize_series(df_a[col_a])
    b = normalize_series(df_b[col_b])

    # Ignore empty values
    a_set = set(a[a != ""])
    b_set = set(b[b != ""])

    only_in_a = sorted(a_set - b_set)   # A có mà B không có
    only_in_b = sorted(b_set - a_set)   # B có mà A không có
    common = sorted(a_set & b_set)

    if not only_in_a and not only_in_b:
        st.success(
            "✅ Dữ liệu trùng khớp giữa 2 file (không có thông tin bị lệch).")
        st.subheader("Dữ liệu trùng khớp")
        st.dataframe(to_df(common, "value"), use_container_width=True)

    else:
        st.error("❌ Dữ liệu KHÔNG trùng khớp giữa 2 file.")

        # ✅ Theo đúng ý bạn: luôn báo “B có mà A không có”
        st.subheader("➕ Dữ liệu có ở File B mà File A KHÔNG có")
        if only_in_b:
            st.dataframe(to_df(only_in_b, "value_only_in_B"),
                         use_container_width=True)
        else:
            st.info("Không có dữ liệu nào chỉ xuất hiện ở File B.")

        st.subheader("➖ Dữ liệu có ở File A mà File B KHÔNG có")
        if only_in_a:
            st.dataframe(to_df(only_in_a, "value_only_in_A"),
                         use_container_width=True)
        else:
            st.info("Không có dữ liệu nào chỉ xuất hiện ở File A.")

        # (Tuỳ chọn) vẫn show common để đối chiếu
        st.subheader("✅ Dữ liệu trùng khớp (để đối chiếu)")
        if common:
            st.dataframe(to_df(common, "value_common"),
                         use_container_width=True)
        else:
            st.info("Không có giá trị trùng khớp.")

    # ---------- Export Excel ----------
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as w:
        to_df(common, "common").to_excel(w, index=False, sheet_name="Common")
        to_df(only_in_a, "only_in_A").to_excel(
            w, index=False, sheet_name="Only_in_A")
        to_df(only_in_b, "only_in_B").to_excel(
            w, index=False, sheet_name="Only_in_B")
    output.seek(0)

    st.download_button(
        "Download report Excel",
        data=output,
        file_name="compare_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
