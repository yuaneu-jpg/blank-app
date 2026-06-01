import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

st.set_page_config(
    page_title="NYC Airbnb Streamlit Dashboard",
    layout="wide"
)

LIGHT_BLUE = "#74A9CF"
DARK_BLUE = "#2B6C9E"
PALE_BLUE = "#D9ECF7"
LIGHT_GRAY = "#E6E6E6"
TEXT_GRAY = "#333333"

alt.data_transformers.disable_max_rows()

@st.cache_data
def load_data():
    possible_paths = [
        Path("listings.csv"),
        Path("listings(1).csv"),
        Path("/listings.csv"),
        Path("/listings(1).csv"),
        Path("/mnt/data/listings(1).csv")
    ]

    csv_path = None
    for path in possible_paths:
        if path.exists():
            csv_path = path
            break

    if csv_path is None:
        st.error("Could not find listings.csv. Make sure the file is in the same folder as streamlit_app.py.")
        st.stop()

    df = pd.read_csv(csv_path)

    numeric_cols = [
        "review_scores_rating",
        "number_of_reviews",
        "accommodates",
        "availability_365",
        "minimum_nights",
        "maximum_nights"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    category_cols = [
        "neighbourhood_cleansed",
        "neighbourhood_group_cleansed",
        "room_type",
        "property_type"
    ]

    for col in category_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace("nan", pd.NA)

    return df
df = load_data()

required_cols = [
    "neighbourhood_cleansed",
    "neighbourhood_group_cleansed",
    "review_scores_rating",
    "number_of_reviews",
    "accommodates",
    "room_type"
]

missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    st.error(f"The dataset is missing these required columns: {missing_cols}")
    st.stop()

st.title("NYC Airbnb Listings Streamlit Dashboard")

st.write(
    """
    This interactive Streamlit dashboard explores Airbnb listing quality and guest capacity across NYC.
    According to the last discussion's EDA, a focus on three connected questions was kept in mind: which neighborhoods have the highest average ratings,
    how review ratings relate to the number of reviews, and which neighborhoods tend to accommodate
    the largest number of guests.
    """
)

st.write(
    """
    Use cross-filters in the sidebar to narrow the dataset. Click a bar on the bar chartsto
    cross-filter the scatterplot and compare that neighborhood across the dashboard. Double click
    a selected bar to clear the selection.
    """
)

st.sidebar.header("Filters")

borough_options = sorted(df["neighbourhood_group_cleansed"].dropna().unique())

selected_boroughs = st.sidebar.multiselect(
    "Select borough(s)",
    options=borough_options,
    default=borough_options
)

room_options = sorted(df["room_type"].dropna().unique())

selected_room_types = st.sidebar.multiselect(
    "Select room type(s)",
    options=room_options,
    default=room_options
)

filtered_df = df.copy()

filtered_df = filtered_df[
    filtered_df["neighbourhood_group_cleansed"].isin(selected_boroughs)
]

filtered_df = filtered_df[
    filtered_df["room_type"].isin(selected_room_types)
]

if len(filtered_df) == 0:
    st.warning("No listings match the selected filters.")
    st.stop()

rated_df = filtered_df.dropna(
    subset=[
        "review_scores_rating",
        "number_of_reviews",
        "neighbourhood_cleansed",
        "neighbourhood_group_cleansed",
        "room_type"
    ]
).copy()

capacity_df_raw = filtered_df.dropna(
    subset=[
        "accommodates",
        "neighbourhood_cleansed",
        "neighbourhood_group_cleansed"
    ]
).copy()
min_neighborhood_listings = 10
top_n = 20

top_rating_df = (
    rated_df
    .groupby("neighbourhood_cleansed", as_index=False)
    .agg(
        average_review_rating=("review_scores_rating", "mean"),
        listing_count=("id", "count"),
        average_reviews=("number_of_reviews", "mean")
    )
)

top_rating_df = top_rating_df[
    top_rating_df["listing_count"] >= min_neighborhood_listings
]

top_rating_df = (
    top_rating_df
    .sort_values("average_review_rating", ascending=False)
    .head(top_n)
)

top_capacity_df = (
    capacity_df_raw
    .groupby("neighbourhood_cleansed", as_index=False)
    .agg(
        average_guest_capacity=("accommodates", "mean"),
        listing_count=("id", "count")
    )
)

top_capacity_df = top_capacity_df[
    top_capacity_df["listing_count"] >= min_neighborhood_listings
]

top_capacity_df = (
    top_capacity_df
    .sort_values("average_guest_capacity", ascending=False)
    .head(top_n)
)

scatter_df = rated_df.copy()

if len(scatter_df) > 8000:
    scatter_df = scatter_df.sample(8000, random_state=42)

trend_df = scatter_df[scatter_df["number_of_reviews"] > 0].copy()


neighborhood_select = alt.selection_point(
    fields=["neighbourhood_cleansed"],
    empty=True,
    on="click",
    clear="dblclick",
    name="Neighborhood"
)
#chart 1
rating_bar = (
    alt.Chart(top_rating_df)
    .mark_bar(cornerRadiusEnd=3)
    .encode(
        x=alt.X(
            "average_review_rating:Q",
            title="Average Review Rating",
            scale=alt.Scale(domain=[0, 5])
        ),
        y=alt.Y(
            "neighbourhood_cleansed:N",
            title="Neighborhood in NYC",
            sort="-x"
        ),
        color=alt.condition(
            neighborhood_select,
            alt.value(DARK_BLUE),
            alt.value(PALE_BLUE)
        ),
        tooltip=[
            alt.Tooltip("neighbourhood_cleansed:N", title="Neighborhood"),
            alt.Tooltip("average_review_rating:Q", title="Average Rating", format=".2f"),
            alt.Tooltip("listing_count:Q", title="Listings"),
            alt.Tooltip("average_reviews:Q", title="Average Reviews", format=".1f")
        ]
    )
    .add_params(neighborhood_select)
    .properties(
        width=850,
        height=400,
        title="Highest Rated NYC Neighborhoods by Average Review Rating"
    )
)


#chart 2

scatter = (
    alt.Chart(scatter_df)
    .mark_circle(size=35, opacity=0.35)
    .encode(
        x=alt.X(
            "number_of_reviews:Q",
            title="Number of Reviews"
        ),
        y=alt.Y(
            "review_scores_rating:Q",
            title="Review Rating",
            scale=alt.Scale(domain=[0, 5])
        ),
        color=alt.condition(
            neighborhood_select,
            alt.Color(
                "neighbourhood_group_cleansed:N",
                title="Borough",
                scale=alt.Scale(
                    scheme="blues"
                )
            ),
            alt.value(LIGHT_GRAY)
        ),
        tooltip=[
            alt.Tooltip("name:N", title="Listing"),
            alt.Tooltip("neighbourhood_cleansed:N", title="Neighborhood"),
            alt.Tooltip("neighbourhood_group_cleansed:N", title="Borough"),
            alt.Tooltip("room_type:N", title="Room Type"),
            alt.Tooltip("review_scores_rating:Q", title="Rating", format=".2f"),
            alt.Tooltip("number_of_reviews:Q", title="Reviews"),
            alt.Tooltip("accommodates:Q", title="Accommodates")
        ]
    )
    .transform_filter(neighborhood_select)
    .properties(
        width=850,
        height=420,
        title="Review Rating vs. Number of Reviews for NYC Listings"
    )
)

trend = (
    alt.Chart(trend_df)
    .transform_filter(neighborhood_select)
    .transform_regression(
        "number_of_reviews",
        "review_scores_rating",
        method="log"
    )
    .mark_line(color=TEXT_GRAY, strokeWidth=3)
    .encode(
        x=alt.X("number_of_reviews:Q"),
        y=alt.Y("review_scores_rating:Q")
    )
)


#chart 3

capacity_bar = (
    alt.Chart(top_capacity_df)
    .mark_bar(cornerRadiusEnd=3)
    .encode(
        x=alt.X(
            "average_guest_capacity:Q",
            title="Average Number of Guests Accommodated"
        ),
        y=alt.Y(
            "neighbourhood_cleansed:N",
            title="Neighborhood in NYC",
            sort="-x"
        ),
        color=alt.condition(
            neighborhood_select,
            alt.value(DARK_BLUE),
            alt.value(PALE_BLUE)
        ),
        tooltip=[
            alt.Tooltip("neighbourhood_cleansed:N", title="Neighborhood"),
            alt.Tooltip("average_guest_capacity:Q", title="Average Capacity", format=".2f"),
            alt.Tooltip("listing_count:Q", title="Listings")
        ]
    )
    .add_params(neighborhood_select)
    .properties(
        width=850,
        height=400,
        title="Most Accommodating NYC Neighborhoods by Average Guest Capacity"
    )
)
#altair
combined_chart = (
    alt.vconcat(
        rating_bar,
        scatter + trend,
        capacity_bar
    )
    .resolve_scale(
        color="independent"
    )
    .configure_view(
        strokeWidth=0
    )
    .configure_axis(
        labelColor=TEXT_GRAY,
        titleColor=TEXT_GRAY,
        gridColor="#EEEEEE"
    )
    .configure_title(
        color=TEXT_GRAY,
        fontSize=16,
        anchor="middle"
    )
    .configure_legend(
        labelColor=TEXT_GRAY,
        titleColor=TEXT_GRAY
    )
)

st.altair_chart(combined_chart, use_container_width=True)
st.subheader("Key Insights")

st.write(
    """
    The highest-rated neighborhoods are tightly clustered with small variations in aggregated ratings near the top of the rating scale,
    which suggests that small differences in average rating need to be interpreted carefully.
    A neighborhood may appear highly rated, but the strength of that pattern depends on how
    many listings and reviews support the average.
    """
)

st.write(
    """
    The scatterplot shows that listings with very few reviews have more variation in rating,
    while listings with many reviews tend to cluster near higher ratings. This suggests that
    review count can act as a rough measure of rating stability. Clicking on the bar for each neighborhood allows users to see where exactly the listings lie within this log pattern.
    """
)

st.write(
    """
    The guest-capacity chart shows a further dimension of the Airbnb listings. Neighborhoods
    that accommodate larger groups are not always the same neighborhoods with the highest
    average ratings, so listing quality and listing capacity should be read as separate patterns. The goal of this dashbaord is to provide a window to view all three different relationships and understand and view statistics based on neighborhoods in NYC.
    """
)