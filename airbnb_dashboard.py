import streamlit as st
import pandas as pd
import altair as alt

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Austin Airbnb Explorer", layout="wide")
st.title("Austin Airbnb Listings Explorer")
st.markdown("Explore Inside Airbnb data for Austin, TX. Use the filters in the sidebar to narrow the dataset — all charts update together.")

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("listings (1).csv")
    df = df[df["price"] <= 1000]
    df = df[df["price"] > 0]
    df["neighbourhood"] = df["neighbourhood"].astype(str)
    df["availability_pct"] = (df["availability_365"] / 365 * 100).round(1)
    return df

df = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.header("Filters")

room_types = ["All"] + sorted(df["room_type"].unique().tolist())
selected_room = st.sidebar.selectbox("Room Type", room_types)

price_min, price_max = int(df["price"].min()), int(df["price"].max())
price_range = st.sidebar.slider("Price per Night ($)", price_min, price_max, (price_min, min(500, price_max)))

min_reviews = st.sidebar.slider("Minimum Number of Reviews", 0, 200, 0)

top_n_zips = st.sidebar.slider("Top N ZIP Codes to Show", 5, 20, 10)

# ── Filter data ───────────────────────────────────────────────────────────────
filtered = df.copy()
if selected_room != "All":
    filtered = filtered[filtered["room_type"] == selected_room]
filtered = filtered[
    (filtered["price"] >= price_range[0]) &
    (filtered["price"] <= price_range[1]) &
    (filtered["number_of_reviews"] >= min_reviews)
]

st.sidebar.markdown(f"**{len(filtered):,} listings** match your filters")

# ── Shared brush for coordination ─────────────────────────────────────────────
# empty=True means ALL points show before any brush is drawn
brush = alt.selection_interval(encodings=["x"], empty=True)

# ── Chart 1: Price Distribution (histogram) ───────────────────────────────────
st.subheader("Price Distribution")
st.caption("Drag to select a price range — the scatter plot and map below will update.")

price_hist = (
    alt.Chart(filtered)
    .mark_bar(opacity=0.8)
    .encode(
        x=alt.X("price:Q", bin=alt.Bin(maxbins=40), title="Price per Night ($)"),
        y=alt.Y("count():Q", title="Number of Listings"),
        color=alt.condition(brush, alt.value("#E87B3E"), alt.value("#cccccc")),
        tooltip=[
            alt.Tooltip("price:Q", bin=alt.Bin(maxbins=40), title="Price Range"),
            alt.Tooltip("count():Q", title="Listings"),
        ],
    )
    .add_params(brush)
    .properties(height=250)
)
st.altair_chart(price_hist, use_container_width=True)

# ── Row 2: Scatter + Map (lat/lon scatter, no projection) ─────────────────────
col1, col2 = st.columns(2)

# Chart 2: Price vs Reviews scatter — brushed
with col1:
    st.subheader("Price vs. Number of Reviews")
    st.caption("Brush the histogram above to filter. Do cheaper listings attract more reviews?")

    scatter = (
        alt.Chart(filtered)
        .mark_circle(opacity=0.4, size=30)
        .encode(
            x=alt.X("price:Q", title="Price per Night ($)"),
            y=alt.Y("number_of_reviews:Q", title="Number of Reviews"),
            color=alt.Color("room_type:N", title="Room Type",
                            scale=alt.Scale(scheme="tableau10")),
            tooltip=[
                alt.Tooltip("name:N", title="Listing"),
                alt.Tooltip("price:Q", title="Price ($)"),
                alt.Tooltip("number_of_reviews:Q", title="# Reviews"),
                alt.Tooltip("room_type:N", title="Room Type"),
            ],
        )
        .transform_filter(brush)
        .properties(height=350)
    )
    st.altair_chart(scatter, use_container_width=True)

# Chart 3: Lat/lon scatter as map (no .project() — avoids rendering issues)
with col2:
    st.subheader("Listing Locations")
    st.caption("Brush the histogram to highlight listings in that price range. Color = room type.")

    map_chart = (
        alt.Chart(filtered)
        .mark_circle(opacity=0.45, size=15)
        .encode(
            x=alt.X("longitude:Q", title="Longitude",
                    scale=alt.Scale(zero=False)),
            y=alt.Y("latitude:Q", title="Latitude",
                    scale=alt.Scale(zero=False)),
            color=alt.condition(
                brush,
                alt.Color("room_type:N", title="Room Type",
                          scale=alt.Scale(scheme="tableau10")),
                alt.value("#dddddd")
            ),
            tooltip=[
                alt.Tooltip("name:N", title="Listing"),
                alt.Tooltip("room_type:N", title="Room Type"),
                alt.Tooltip("price:Q", title="Price ($)"),
                alt.Tooltip("neighbourhood:N", title="ZIP Code"),
            ],
        )
        .transform_filter(brush)
        .properties(height=350)
    )
    st.altair_chart(map_chart, use_container_width=True)

# ── Chart 4: Avg Price by ZIP Code ────────────────────────────────────────────
st.subheader(f"Average Price by ZIP Code (Top {top_n_zips})")
st.caption("Ranked by average nightly price within your filtered selection.")

zip_agg = (
    filtered.groupby("neighbourhood")["price"]
    .agg(["mean", "count"])
    .reset_index()
    .rename(columns={"mean": "avg_price", "count": "listings"})
    .sort_values("avg_price", ascending=False)
    .head(top_n_zips)
)

zip_bar = (
    alt.Chart(zip_agg)
    .mark_bar()
    .encode(
        x=alt.X("avg_price:Q", title="Average Price ($)"),
        y=alt.Y("neighbourhood:N", sort="-x", title="ZIP Code"),
        color=alt.Color("avg_price:Q", scale=alt.Scale(scheme="oranges"), legend=None),
        tooltip=[
            alt.Tooltip("neighbourhood:N", title="ZIP Code"),
            alt.Tooltip("avg_price:Q", title="Avg Price ($)", format=".2f"),
            alt.Tooltip("listings:Q", title="# Listings"),
        ],
    )
    .properties(height=max(200, top_n_zips * 28))
)
st.altair_chart(zip_bar, use_container_width=True)

# ── Chart 5: Room type breakdown ──────────────────────────────────────────────
st.subheader("Listings by Room Type")

room_counts = filtered["room_type"].value_counts().reset_index()
room_counts.columns = ["room_type", "count"]

room_bar = (
    alt.Chart(room_counts)
    .mark_bar()
    .encode(
        x=alt.X("count:Q", title="Number of Listings"),
        y=alt.Y("room_type:N", sort="-x", title="Room Type"),
        color=alt.Color("room_type:N", scale=alt.Scale(scheme="tableau10"), legend=None),
        tooltip=["room_type:N", "count:Q"],
    )
    .properties(height=180)
)
st.altair_chart(room_bar, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Data source: [Inside Airbnb](https://insideairbnb.com/get-the-data/) · Austin, TX")
