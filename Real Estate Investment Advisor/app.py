import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from scipy import stats

# ------------------------------
# Page config
# ------------------------------
st.set_page_config(
    page_title=" Real Estate EDA Dashboard",
    layout="wide",
    page_icon="🏡",
)
st.markdown("""
<style>
.stApp {
    background-color: #e0e0e0; 
}
[data-testid="stSidebar"] {
    background-color: #f0f0f0;
}
</style>
""", unsafe_allow_html=True)

st.title(" 🏡 Real Estate EDA Dashboard")

# ------------------------------
# Helper: load & clean (cached)
# ------------------------------
@st.cache_data(ttl=60)  # cache for 60 seconds, helps "real-time" refresh
def load_and_clean(path="india_housing_prices.csv"):
    df = pd.read_csv(path)

    # canonicalize column names (strip & lower for robust matching)
    df.columns = [c.strip() for c in df.columns]

    # Basic cleaning
    df = df.drop_duplicates().copy()

    # Fill missing numeric with median, categorical with Unknown
    num_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
    for c in num_cols:
        df[c] = df[c].fillna(df[c].median())
    for c in cat_cols:
        df[c] = df[c].fillna("Unknown")

    # Feature engineering: unify possible column names
    # Price column detection (common names)
    price_col = None
    for cand in ["Price", "Price_in_Lakhs", "Price_in_lakhs", "Price (Lakhs)", "Price_Lakhs"]:
        if cand in df.columns:
            price_col = cand
            break
    if price_col is None:
        # try case-insensitive fallback
        for col in df.columns:
            if "price" in col.lower():
                price_col = col
                break
    if price_col is None:
        raise ValueError("No price column found in CSV. Rename your price column to contain 'price'.")

    # Area column detection
    area_col = None
    for cand in ["Size_in_SqFt", "Area", "Area_in_SqFt", "Size", "Size (SqFt)"]:
        if cand in df.columns:
            area_col = cand
            break
    if area_col is None:
        for col in df.columns:
            if "sqft" in col.lower() or "size" in col.lower() or "area" in col.lower():
                area_col = col
                break
    if area_col is None:
        raise ValueError("No area/size column found in CSV. Rename your area column to contain 'area' or 'sqft' or 'size'.")

    # Standardize column names used downstream
    df = df.rename(columns={price_col: "Price", area_col: "Area"})

    # Ensure Price is in Lakhs: if Price seems very large (>5000), assume it's in rupees or absolute
    if df["Price"].median() > 5000:
        df["Price_in_Lakhs"] = df["Price"] / 100000.0
    else:
        df["Price_in_Lakhs"] = df["Price"]

    # Price per sq ft
    df["Price_per_SqFt"] = (df["Price_in_Lakhs"] * 100000.0) / (df["Area"].replace(0, np.nan))
    df["Price_per_SqFt"] = df["Price_per_SqFt"].fillna(df["Price_per_SqFt"].median())

    # Nearby schools/hospitals defaults if missing
    if "Nearby_Schools" not in df.columns:
        df["Nearby_Schools"] = 0
    if "Nearby_Hospitals" not in df.columns:
        df["Nearby_Hospitals"] = 0

    # Amenities count if present as comma-separated
    if "Amenities" in df.columns:
        df["Amenities"] = df["Amenities"].fillna("").apply(
            lambda x: 0 if str(x).strip() == "" else len([a for a in str(x).split(",") if a.strip() != ""])
        )
    else:
        df["Amenities"] = 0

    # School density normalized 0-1
    if df["Nearby_Schools"].max() > 0:
        df["School_Density_Score"] = df["Nearby_Schools"] / df["Nearby_Schools"].max()
    else:
        df["School_Density_Score"] = 0.0

    # Good_Investment heuristic label for EDA (city-median + school-density)
    if "Good_Investment" not in df.columns:
        city_med = df.groupby("City")["Price_per_SqFt"].transform("median")
        school_med = df["School_Density_Score"].median()
        df["Good_Investment"] = np.where(
            (df["Price_per_SqFt"] < city_med) & (df["School_Density_Score"] > school_med), 1, 0
        )

    return df

# ------------------------------
# Top bar + load
# ------------------------------
col_refresh, col_info = st.columns([1, 3])
with col_refresh:
    if st.button("🔄 Refresh Data"):
        # clearing cache will force reload (works with st.cache_data)
        st.cache_data.clear()
        st.rerun()


with col_info:
    st.markdown("Use the sidebar to filter the dataset. Download cleaned data or inspect charts in real time.")

try:
    df = load_and_clean("india_housing_prices.csv")
except Exception as e:
    st.error(f"Data load error: {e}")
    st.stop()

# ------------------------------
# Sidebar filters
# ------------------------------
st.sidebar.header("🔎 Filters & Options")
cities = sorted(df["City"].dropna().unique())
city_sel = st.sidebar.multiselect("City (multi)", options=cities, default=cities[:6])

prop_types = sorted(df["Property_Type"].dropna().unique()) if "Property_Type" in df.columns else []
ptype_sel = st.sidebar.multiselect("Property Type", options=prop_types, default=prop_types[:3])

min_bhk = int(df["BHK"].min()) if "BHK" in df.columns else 1
max_bhk = int(df["BHK"].max()) if "BHK" in df.columns else 5
bhk_sel = st.sidebar.slider("BHK range", min_bhk, max_bhk, (min_bhk, min(max_bhk, min_bhk+2)))

min_price = float(df["Price_in_Lakhs"].min())
max_price = float(df["Price_in_Lakhs"].max())
price_sel = st.sidebar.slider("Price (Lakhs)", min_price, max_price, (min_price, min_price + (max_price-min_price)/4))

area_min = float(df["Area"].min())
area_max = float(df["Area"].max())
area_sel = st.sidebar.slider("Area (SqFt)", area_min, area_max, (area_min, area_min + (area_max-area_min)/4))

show_outliers = st.sidebar.checkbox("Show outliers table", value=False)
download_clean = st.sidebar.checkbox("Show download cleaned data", value=True)

# ------------------------------
# Apply filters
# ------------------------------
filtered = df.copy()
if city_sel:
    filtered = filtered[filtered["City"].isin(city_sel)]
if ptype_sel:
    filtered = filtered[filtered["Property_Type"].isin(ptype_sel)]
if "BHK" in filtered.columns:
    filtered = filtered[(filtered["BHK"] >= bhk_sel[0]) & (filtered["BHK"] <= bhk_sel[1])]
filtered = filtered[(filtered["Price_in_Lakhs"] >= price_sel[0]) & (filtered["Price_in_Lakhs"] <= price_sel[1])]
filtered = filtered[(filtered["Area"] >= area_sel[0]) & (filtered["Area"] <= area_sel[1])]

# ------------------------------
# Top metrics
# ------------------------------
st.metric(label="Filtered properties", value=len(filtered))
col1, col2, col3, col4 = st.columns(4)
col1.metric("Avg Price (Lakhs)", f"{filtered['Price_in_Lakhs'].mean():.2f}")
col2.metric("Median Price/SqFt", f"{filtered['Price_per_SqFt'].median():.0f}")
col3.metric("Avg Area (SqFt)", f"{filtered['Area'].mean():.0f}")
col4.metric("Good Investment %", f"{filtered['Good_Investment'].mean()*100:.1f}%")

# ------------------------------
# Main layout — charts
# ------------------------------
st.markdown("### 📈 Price & Location Insights")
row1_col1, row1_col2 = st.columns([2, 1])

with row1_col1:
    st.subheader("Average Price by City")
    city_trend = filtered.groupby("City")["Price_in_Lakhs"].mean().reset_index().sort_values("Price_in_Lakhs", ascending=False)
    fig_city = px.bar(city_trend, x="City", y="Price_in_Lakhs", title="Avg Price by City", text_auto=".2s")
    fig_city.update_layout(xaxis_tickangle=-45, height=470)
    st.plotly_chart(fig_city, use_container_width=True)

with row1_col2:
    st.subheader("Price per SqFt Distribution")
    fig_hist = px.histogram(filtered, x="Price_per_SqFt", nbins=40, title="Price per SqFt Distribution")
    st.plotly_chart(fig_hist, use_container_width=True)

st.markdown("---")
st.subheader("📊 Interactive Scatter & Filters")

left_col, right_col = st.columns([1, 1])
with left_col:
    st.subheader("Top Localities by Median Price")
    top_local = filtered.groupby("Locality")["Price_in_Lakhs"].median().sort_values(ascending=False).head(10).reset_index()
    st.table(top_local)

with right_col:
    st.markdown("**Size vs Price (interactive)** — use lasso/box select to inspect points")
    fig_scatter = px.scatter(
        filtered,
        x="Area",
        y="Price_in_Lakhs",
        color="City" if filtered["City"].nunique() <= 10 else None,
        hover_data=["Locality", "Property_Type", "BHK", "Price_per_SqFt"],
        title="Area vs Price",
        height=420
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    
st.markdown("---")
st.subheader("🗺️ Heatmap: City × Property Type (Avg Price)")
# heatmap (pivot)
if "Property_Type" in filtered.columns:
    pivot = filtered.pivot_table(values="Price_in_Lakhs", index="City", columns="Property_Type", aggfunc="mean").fillna(0)
    fig_heat = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale="Viridis"
    ))
    fig_heat.update_layout(height=500, title="Avg Price (Lakhs) — City × Property Type")
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.info("No Property_Type column available for heatmap.")

st.markdown("---")
st.subheader("🔗 Correlation Matrix (numeric features)")
numeric_cols = ["Price_in_Lakhs", "Area", "Price_per_SqFt", "Nearby_Schools", "Nearby_Hospitals", "Amenities_Count"]
numeric_present = [c for c in numeric_cols if c in filtered.columns]
if len(numeric_present) >= 2:
    corr = filtered[numeric_present].corr()
    fig_corr = px.imshow(corr, text_auto=True, aspect="auto", title="Correlation Matrix")
    st.plotly_chart(fig_corr, use_container_width=True)
else:
    st.info("Not enough numeric columns to show correlation matrix.")

# ------------------------------
# Outlier table (optional)
# ------------------------------
if show_outliers:
    st.markdown("---")
    st.subheader("⚠️ Outliers (z-score > 3 in Price_per_SqFt or Area)")
    tmp = filtered.copy()
    tmp["z_pps"] = np.abs(stats.zscore(tmp["Price_per_SqFt"].fillna(tmp["Price_per_SqFt"].median())))
    tmp["z_area"] = np.abs(stats.zscore(tmp["Area"].fillna(tmp["Area"].median())))
    outliers = tmp[(tmp["z_pps"] > 3) | (tmp["z_area"] > 3)].sort_values(by=["z_pps"], ascending=False)
    st.dataframe(outliers.head(100))

# ------------------------------
# Quick EDA explorer
# ------------------------------
st.markdown("---")
st.subheader("🔎 Quick Explorations")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown("**Price per SqFt by Furnishing**")
    if "Furnished_Status" in filtered.columns:
        fig = px.box(filtered, x="Furnished_Status", y="Price_per_SqFt", title="Price per SqFt by Furnishing")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No Furnished_Status column")

with col_b:
    st.markdown("**Price by BHK**")
    if "BHK" in filtered.columns:
        fig = px.box(filtered, x="BHK", y="Price_in_Lakhs", title="Price by BHK")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No BHK column")

with col_c:
    st.markdown("**Public Transport vs Price/SqFt**")
    if "Public_Transport_Accessibility" in filtered.columns:
        fig = px.box(filtered, x="Public_Transport_Accessibility", y="Price_per_SqFt", title="PTA vs Price/SqFt")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No Public_Transport_Accessibility column")

# ------------------------------
# Download cleaned data
# ------------------------------
if download_clean:
    st.markdown("---")
    st.subheader("⬇️ Download cleaned dataset")
    to_download = filtered.copy()
    csv_bytes = to_download.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv_bytes, file_name="cleaned_india_housing_filtered.csv", mime="text/csv")

# ------------------------------
# Footer / notes
# ------------------------------
st.markdown("---")
st.markdown(
    "Built for quick interactive EDA. Use the **Refresh Data** button to reload the CSV (useful when the source file updates). "
)
