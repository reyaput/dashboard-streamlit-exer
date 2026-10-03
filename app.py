"""Streamlit customer dashboard."""

import pandas as pd
import plotly.express as px
import streamlit as st

from db import fetch_all


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


st.title("Customer Master")
st.caption("Ringkasan pelanggan dari database MySQL")

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
