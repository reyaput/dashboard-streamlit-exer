"""Streamlit customer dashboard."""

from time import perf_counter

import pandas as pd
import plotly.express as px
import streamlit as st

from db import fetch_all, get_connection


MAX_QUERY_HISTORY = 10
QUERY_HISTORY_KEY = "sql_query_history"
QUERY_INPUT_KEY = "sql_runner_query"


st.set_page_config(
    page_title="Customer Master Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
)


@st.cache_data(ttl=300)
def load_customers() -> pd.DataFrame:
    """Load customer records from MySQL."""
    rows = fetch_all(
        """SELECT customer_id, customer_name, customer_age, gender,
                  customer_segment, customer_city, customer_state,
                  customer_country, region, customer_postal_code,
                  customer_acquisition_cost
           FROM customer_master"""
    )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["customer_acquisition_cost"] = pd.to_numeric(
            frame["customer_acquisition_cost"]
        )
    return frame


def split_sql_statements(query: str) -> list[str]:
    """Split SQL into statements while ignoring semicolons in strings/comments."""
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    index = 0

    while index < len(query):
        char = query[index]
        next_char = query[index + 1] if index + 1 < len(query) else ""

        if in_line_comment:
            current.append(char)
            if char == "\n":
                in_line_comment = False
            index += 1
            continue

        if in_block_comment:
            current.append(char)
            if char == "*" and next_char == "/":
                current.append(next_char)
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue

        if in_single:
            current.append(char)
            if char == "\\" and next_char:
                current.append(next_char)
                index += 2
                continue
            if char == "'":
                in_single = False
            index += 1
            continue

        if in_double:
            current.append(char)
            if char == "\\" and next_char:
                current.append(next_char)
                index += 2
                continue
            if char == '"':
                in_double = False
            index += 1
            continue

        if in_backtick:
            current.append(char)
            if char == "`":
                in_backtick = False
            index += 1
            continue

        if char == "#":
            current.append(char)
            in_line_comment = True
            index += 1
            continue

        if (
            char == "-"
            and next_char == "-"
            and (index + 2 >= len(query) or query[index + 2].isspace())
        ):
            current.append(char)
            current.append(next_char)
            in_line_comment = True
            index += 2
            continue

        if char == "/" and next_char == "*":
            current.append(char)
            current.append(next_char)
            in_block_comment = True
            index += 2
            continue

        if char == "'":
            current.append(char)
            in_single = True
            index += 1
            continue

        if char == '"':
            current.append(char)
            in_double = True
            index += 1
            continue

        if char == "`":
            current.append(char)
            in_backtick = True
            index += 1
            continue

        if char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            index += 1
            continue

        current.append(char)
        index += 1

    last_statement = "".join(current).strip()
    if last_statement:
        statements.append(last_statement)

    return statements


def is_data_changing_query(query: str) -> bool:
    """Return True when query likely changes database data/schema."""
    mutating_keywords = {
        "insert",
        "update",
        "delete",
        "replace",
        "create",
        "alter",
        "drop",
        "truncate",
        "rename",
        "grant",
        "revoke",
        "set",
        "call",
    }

    remaining = query
    while True:
        remaining = remaining.lstrip()
        if remaining.startswith("--") or remaining.startswith("#"):
            line_end = remaining.find("\n")
            if line_end == -1:
                remaining = ""
                break
            remaining = remaining[line_end + 1 :]
            continue
        if remaining.startswith("/*"):
            block_end = remaining.find("*/")
            if block_end == -1:
                remaining = ""
                break
            remaining = remaining[block_end + 2 :]
            continue
        break

    first_word: list[str] = []
    for char in remaining:
        if char.isalpha():
            first_word.append(char.lower())
        elif first_word:
            break
    return "".join(first_word) in mutating_keywords


def add_query_to_history(query: str) -> None:
    """Store latest unique queries in session state."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return

    history = st.session_state.setdefault(QUERY_HISTORY_KEY, [])
    if cleaned_query in history:
        history.remove(cleaned_query)
    history.insert(0, cleaned_query)
    st.session_state[QUERY_HISTORY_KEY] = history[:MAX_QUERY_HISTORY]


def render_result_chart(result_df: pd.DataFrame) -> None:
    """Render a chart from SQL result data if columns are compatible."""
    st.subheader("Chart hasil query")

    if result_df.empty:
        st.info("Hasil query kosong, chart tidak dapat ditampilkan.")
        return

    if len(result_df.columns) < 2:
        st.info("Minimal dibutuhkan 2 kolom untuk membuat chart.")
        return

    numeric_columns = [
        column for column in result_df.columns if pd.api.types.is_numeric_dtype(result_df[column])
    ]
    if not numeric_columns:
        st.info("Tidak ada kolom numerik yang bisa dipakai sebagai sumbu Y.")
        return

    chart_type = st.selectbox(
        "Jenis chart",
        options=["bar", "line", "scatter"],
        key="sql_chart_type",
    )
    x_column = st.selectbox("Kolom X", options=list(result_df.columns), key="sql_chart_x")
    y_column = st.selectbox("Kolom Y", options=numeric_columns, key="sql_chart_y")

    try:
        if chart_type == "bar":
            figure = px.bar(result_df, x=x_column, y=y_column)
        elif chart_type == "line":
            figure = px.line(result_df, x=x_column, y=y_column)
        else:
            figure = px.scatter(result_df, x=x_column, y=y_column)
        st.plotly_chart(figure, use_container_width=True)
    except Exception as error:
        st.warning(f"Chart tidak dapat ditampilkan untuk kombinasi kolom tersebut: {error}")


st.title("Customer Master")
st.caption("Ringkasan pelanggan dari database MySQL")

dashboard_tab, sql_runner_tab = st.tabs(["Dashboard", "SQL Query Runner"])

with dashboard_tab:
    try:
        customers = load_customers()
    except Exception as error:
        st.error("Data belum dapat dimuat dari MySQL.")
        st.code(str(error))
        st.stop()

    if customers.empty:
        st.warning("Tabel customer_master belum memiliki data. Jalankan import_data.py.")
        st.stop()

    with st.sidebar:
        st.header("Filter")
        selected_regions = st.multiselect(
            "Region",
            sorted(customers["region"].dropna().unique()),
        )
        selected_segments = st.multiselect(
            "Segment",
            sorted(customers["customer_segment"].dropna().unique()),
        )
        selected_countries = st.multiselect(
            "Country",
            sorted(customers["customer_country"].dropna().unique()),
        )

    filtered = customers.copy()
    if selected_regions:
        filtered = filtered[filtered["region"].isin(selected_regions)]
    if selected_segments:
        filtered = filtered[filtered["customer_segment"].isin(selected_segments)]
    if selected_countries:
        filtered = filtered[filtered["customer_country"].isin(selected_countries)]

    metric_columns = st.columns(4)
    metric_columns[0].metric("Customers", f"{len(filtered):,}")
    metric_columns[1].metric("Avg. age", f"{filtered['customer_age'].mean():.1f}")
    metric_columns[2].metric(
        "Avg. acquisition cost",
        f"${filtered['customer_acquisition_cost'].mean():,.2f}",
    )
    metric_columns[3].metric("Countries", f"{filtered['customer_country'].nunique():,}")

    left_chart, right_chart = st.columns(2)
    with left_chart:
        segment_counts = (
            filtered["customer_segment"]
            .value_counts()
            .rename_axis("segment")
            .reset_index(name="customers")
        )
        st.plotly_chart(
            px.bar(
                segment_counts,
                x="segment",
                y="customers",
                title="Customers by segment",
                color="segment",
            ),
            use_container_width=True,
        )

    with right_chart:
        region_counts = (
            filtered["region"]
            .value_counts()
            .rename_axis("region")
            .reset_index(name="customers")
        )
        st.plotly_chart(
            px.bar(
                region_counts,
                x="region",
                y="customers",
                title="Customers by region",
                color="region",
            ),
            use_container_width=True,
        )

    st.subheader("Customer records")
    st.dataframe(
        filtered.sort_values("customer_id"),
        use_container_width=True,
        hide_index=True,
        column_config={
            "customer_acquisition_cost": st.column_config.NumberColumn(
                "Acquisition cost", format="$%.2f"
            )
        },
    )

with sql_runner_tab:
    st.subheader("SQL Query Runner")

    st.session_state.setdefault(QUERY_INPUT_KEY, "")
    history = st.session_state.setdefault(QUERY_HISTORY_KEY, [])

    if history:
        selected_history = st.selectbox(
            "Riwayat query",
            options=["(Pilih query sebelumnya)"] + history,
            key="sql_history_select",
        )
        if (
            selected_history != "(Pilih query sebelumnya)"
            and st.button("Gunakan query terpilih", key="use_selected_query")
        ):
            st.session_state[QUERY_INPUT_KEY] = selected_history

    with st.form("sql_runner_form", clear_on_submit=False):
        query_text = st.text_area(
            "SQL Query",
            key=QUERY_INPUT_KEY,
            placeholder="Contoh: SELECT * FROM customer_master LIMIT 10;",
            height=180,
        )
        run_query = st.form_submit_button("Run Query")

    if run_query:
        statements = split_sql_statements(query_text)

        if not query_text.strip():
            st.warning("Masukkan SQL query terlebih dahulu.")
        elif not statements:
            st.warning("Query kosong atau hanya berisi komentar.")
        elif len(statements) > 1:
            st.error(
                "Hanya satu statement SQL yang diizinkan per eksekusi. "
                "Pisahkan dan jalankan statement secara terpisah."
            )
        else:
            statement = statements[0]
            add_query_to_history(statement)

            connection = None
            cursor = None
            started_at = perf_counter()

            try:
                connection = get_connection()
                cursor = connection.cursor(dictionary=True)
                cursor.execute(statement)

                if cursor.description is not None:
                    rows = cursor.fetchall()
                    elapsed = perf_counter() - started_at
                    result_df = pd.DataFrame(rows)

                    st.success(
                        f"Query berhasil dijalankan dalam {elapsed:.3f} detik. "
                        f"Jumlah baris: {len(result_df):,}."
                    )
                    st.dataframe(result_df, use_container_width=True, hide_index=True)

                    csv_data = result_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download hasil (CSV)",
                        data=csv_data,
                        file_name="query_result.csv",
                        mime="text/csv",
                    )

                    render_result_chart(result_df)
                else:
                    connection.commit()
                    elapsed = perf_counter() - started_at
                    st.success(
                        "Query non-result berhasil dijalankan dan di-commit. "
                        f"Baris terdampak: {cursor.rowcount}. "
                        f"Waktu eksekusi: {elapsed:.3f} detik."
                    )

                    if is_data_changing_query(statement):
                        load_customers.clear()
            except Exception as error:
                st.error(f"MySQL error: {error}")
            finally:
                if cursor is not None:
                    try:
                        cursor.close()
                    except Exception:
                        pass
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:
                        pass
