"""
app.py
Streamlit Dashboard - Video Game Sales & Engagement Insights
Connects to video_games_cleaned.db (SQLite) or loads Cleaned_VideoGame_Data.csv if DB missing.
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from PIL import Image
from pathlib import Path

# ---- Page layout ----
st.set_page_config(page_title="Video Game Analytics", page_icon="🎮", layout="wide")
BASE_DIR = Path(__file__).parent



# ---- Header / Logo ----
with st.sidebar:
    logo_path = BASE_DIR / "assets" / "logo.png"
    try:
        logo = Image.open(logo_path)
        st.image(logo, width=200)
    except Exception:
        st.markdown("## 🎮 Video Game Analytics")

st.sidebar.markdown("---")
st.sidebar.markdown("**Filters & Settings**")

# ---- Load data (SQLite preferred, fallback to CSV) ----
@st.cache_data(show_spinner=False)
def load_data():
    db_path = BASE_DIR / "video_games_cleaned.db"
    csv_path = BASE_DIR / "Cleaned_VideoGame_Data.csv"

    if db_path.exists():
        conn = sqlite3.connect(db_path)
        # If a 'merged' table exists use it; otherwise join on title/name (best-effort)
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
        table_list = tables['name'].tolist()
        if 'merged' in table_list:
            df = pd.read_sql("SELECT * FROM merged", conn)
        elif 'video_game_data' in table_list:
            df = pd.read_sql("SELECT * FROM video_game_data", conn)
        else:
            # attempt to read games & sales and merge
            if 'games' in table_list and 'sales' in table_list:
                g = pd.read_sql("SELECT * FROM games", conn)
                s = pd.read_sql("SELECT * FROM sales", conn)
                # attempt case-insensitive merge on title/name (best-effort)
                g['title_lc'] = g['Title'].astype(str).str.lower().str.strip()
                s['name_lc'] = s['Name'].astype(str).str.lower().str.strip()
                merged = pd.merge(g, s, left_on='title_lc', right_on='name_lc', how='outer', suffixes=('_games','_sales'))
                df = merged
            else:
                # fallback to CSV
                conn.close()
                df = pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()
        conn.close()
    else:
        df = pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()

    # unify columns (lowercase names for easier coding)
    df.columns = [c.strip() for c in df.columns]
    return df

df = load_data()
if df.empty:
    st.error("No data found. Put `video_games_cleaned.db` or `Cleaned_VideoGame_Data.csv` in the project folder.")
    st.stop()

# ---- Sidebar filters ----
# Normalize col names for filter choices
cols = [c.lower() for c in df.columns]
# possible columns (not guaranteed)
platform_col = next((c for c in df.columns if c.lower().startswith("platform")), None)
genre_col = next((c for c in df.columns if "genre" in c.lower()), None)
title_col = next((c for c in df.columns if c.lower().startswith("title") or c.lower().startswith("name")), None)
rating_col = next((c for c in df.columns if c.lower() == "rating"), None)
global_sales_col = next((c for c in df.columns if "global" in c.lower() and "sales" in c.lower()), None)

platforms = df[platform_col].dropna().unique().tolist() if platform_col else []
genres = df[genre_col].dropna().unique().tolist() if genre_col else []

selected_platforms = st.sidebar.multiselect("Platform(s)", sorted(platforms), default=None)
selected_genres = st.sidebar.multiselect("Genre(s)", sorted(genres), default=None)
min_rating = st.sidebar.slider("Min rating", 0.0, 5.0, 0.0, step=0.1) if rating_col else None
search_title = st.sidebar.text_input("Search title contains")

# apply filters
filtered = df.copy()
if platform_col and selected_platforms:
    filtered = filtered[filtered[platform_col].isin(selected_platforms)]
if genre_col and selected_genres:
    filtered = filtered[filtered[genre_col].isin(selected_genres)]
if rating_col:
    filtered[rating_col] = pd.to_numeric(filtered[rating_col], errors='coerce')
    filtered = filtered[filtered[rating_col].fillna(0) >= min_rating]
if search_title and title_col:
    filtered = filtered[filtered[title_col].astype(str).str.contains(search_title, case=False, na=False)]

# ---- Top row KPIs ----
st.title("🎮 Video Game Sales & Engagement Insights")
kpi1, kpi2, kpi3, kpi4 = st.columns([1.5, 1, 1, 1])

total_sales = filtered[global_sales_col].sum() if global_sales_col in filtered.columns else 0
avg_rating = filtered[rating_col].mean() if rating_col in filtered.columns else None
unique_games = filtered[title_col].nunique() if title_col in filtered.columns else filtered.shape[0]
avg_wishlist = filtered['Wishlist'].mean() if 'Wishlist' in filtered.columns else None

kpi1.metric("💰 Total Global Sales (sum)", f"{total_sales:,.2f}")
kpi2.metric("⭐ Avg Rating", f"{avg_rating:.2f}" if avg_rating is not None else "N/A")
kpi3.metric("🎯 Unique Games", f"{unique_games:,}")
kpi4.metric("💡 Avg Wishlist", f"{avg_wishlist:.0f}" if avg_wishlist is not None else "N/A")

st.markdown("---")

# ---- Tabs: Overview, Genre, Platform, Consumer ----
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Genre Insights", "Platform Insights", "Consumer Behavior", "📊 Power BI Q&A"])


with tab1:
    st.header("Overview")
    st.markdown("High-level trends and time series")

    # Yearly sales if year exists
    year_col = next((c for c in df.columns if c.lower() == 'year' or 'year' in c.lower() and 'sales' not in c.lower()), None)
    if year_col and global_sales_col and year_col in filtered.columns:
        yearly = filtered.groupby(year_col)[global_sales_col].sum().reset_index().sort_values(year_col)
        fig = px.line(yearly, x=year_col, y=global_sales_col, markers=True, title="Global Sales by Year")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Year or Global Sales column not found for time series.")

    st.markdown("### Top Global Sellers")
    if global_sales_col:
        top10 = filtered.sort_values(by=global_sales_col, ascending=False).head(10)
        if title_col:
            st.dataframe(top10[[title_col, global_sales_col]].rename(columns={title_col: "Title", global_sales_col: "Global_Sales"}))
        else:
            st.dataframe(top10.head(10))
    else:
        st.info("No Global_Sales column available in data.")

with tab2:
    st.header("Genre Insights")
    if genre_col:
        genre_sales = filtered.groupby(genre_col)[global_sales_col].sum().reset_index().sort_values(by=global_sales_col, ascending=False)
        figg = px.bar(genre_sales.head(15), x=global_sales_col, y=genre_col, orientation='h', title="Top Genres by Global Sales", labels={global_sales_col:"Global Sales", genre_col:"Genre"})
        st.plotly_chart(figg, use_container_width=True)

        # ratings by genre
        if rating_col:
            genre_rating = filtered.groupby(genre_col)[rating_col].mean().reset_index().sort_values(by=rating_col, ascending=False)
            f2 = px.bar(genre_rating.head(15), x=rating_col, y=genre_col, orientation='h', title="Avg Rating by Genre")
            st.plotly_chart(f2, use_container_width=True)
    else:
        st.info("No genre column found in data.")

with tab3:
    st.header("Platform Insights")
    if platform_col:
        platform_sales = filtered.groupby(platform_col)[global_sales_col].sum().reset_index().sort_values(by=global_sales_col, ascending=False)
        f3 = px.bar(platform_sales.head(15), x=platform_col, y=global_sales_col, title="Top Platforms by Global Sales")
        st.plotly_chart(f3, use_container_width=True)

        # platform vs rating scatter (use filtered data, replace NaNs)
        if rating_col:
            platform_rating = filtered.groupby(platform_col, as_index=False).agg({
                global_sales_col: 'sum',
                rating_col: 'mean'
            }).rename(columns={global_sales_col: 'Total_Sales', rating_col: 'Avg_Rating'})

            platform_rating['Total_Sales'] = platform_rating['Total_Sales'].fillna(0)
            platform_rating['Avg_Rating'] = platform_rating['Avg_Rating'].fillna(0)

            f4 = px.scatter(
                platform_rating,
                x='Total_Sales',
                y='Avg_Rating',
                size='Total_Sales',
                hover_name=platform_col,
                title="Platform: Total Sales vs Avg Rating",
                size_max=50,
                color='Avg_Rating',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(f4, use_container_width=True)
    else:
        st.info("No platform column found in data.")

with tab4:
    st.header("Consumer Behavior")
    
    # Ensure numeric columns
    filtered['Wishlist'] = pd.to_numeric(filtered['Wishlist'], errors='coerce').fillna(0)
    filtered['Plays'] = pd.to_numeric(filtered['Plays'], errors='coerce').fillna(0)

    # Scatter Wishlist vs Sales colored by rating
    f5 = px.scatter(
        filtered,
        x='Wishlist',
        y=global_sales_col,
        size='Plays' if 'Plays' in filtered.columns else None,
        color=rating_col if rating_col else None,
        hover_name=title_col if title_col else None,
        title="Wishlist vs Global Sales (bubble size=Plays, color=Rating)",
        color_continuous_scale='Plasma',
        size_max=50
    )
    st.plotly_chart(f5, use_container_width=True)

    # Optional: Plays distribution histogram
    if 'Plays' in filtered.columns:
        st.markdown("### Distribution of Plays")
        fig_plays = px.histogram(filtered, x='Plays', nbins=30, title="Distribution of Plays")
        st.plotly_chart(fig_plays, use_container_width=True)

    # Optional: Top Wishlist games
    st.markdown("### Top Wishlist Games")
    if title_col:
        top_wishlist = filtered.sort_values('Wishlist', ascending=False).head(10)
        st.dataframe(top_wishlist[[title_col, 'Wishlist', global_sales_col, rating_col]].rename(columns={
            title_col: 'Title', global_sales_col: 'Global Sales', rating_col: 'Rating'
        }))

with tab5:
    st.header("📊 Power BI Style: Answerable Questions (Games + Sales)")

    # ---------------- Sidebar Filters ----------------
    st.sidebar.markdown("### 🎛️ Dashboard Filters (Power BI Style)")
    if 'Genre' in df.columns:
        genre_filter = st.sidebar.multiselect("🎮 Select Genre(s):", sorted(df['Genre'].dropna().unique()))
    else:
        genre_filter = []

    if 'Platform' in df.columns:
        platform_filter = st.sidebar.multiselect("🕹️ Select Platform(s):", sorted(df['Platform'].dropna().unique()))
    else:
        platform_filter = []

    if 'Year' in df.columns:
        min_year, max_year = int(df['Year'].min()), int(df['Year'].max())
        year_range = st.sidebar.slider("📅 Select Year Range:", min_year, max_year, (min_year, max_year))
    else:
        year_range = None

    filtered = df.copy()
    if genre_filter:
        filtered = filtered[filtered['Genre'].isin(genre_filter)]
    if platform_filter:
        filtered = filtered[filtered['Platform'].isin(platform_filter)]
    if year_range and 'Year' in filtered.columns:
        filtered = filtered[(filtered['Year'] >= year_range[0]) & (filtered['Year'] <= year_range[1])]

    # ---------------- Question Selection ----------------
    st.markdown("### ❓ Choose a Business Question")
    question = st.selectbox(
        "Select a question to visualize:",
        [
            # Games metadata
            "🌟 Top-rated games by user reviews",
            "🧑‍🤝‍🧑 Developers with highest average ratings",
            "🧩 Most common genres",
            "⏳ Games with highest backlog vs wishlist",
            "🗓️ Game release trend across years",
            "🔎 Distribution of user ratings",
            "🧑 Top 10 most wishlisted games",
            "🔬 Average number of plays per genre",
            "🏢 Most productive & impactful developers",

            # Sales data
            "🌍 Region with highest game sales",
            "🕹️ Best-selling platforms",
            "📅 Trend of game releases and sales over years",
            "🏢 Top publishers by sales",
            "🔝 Top 10 best-selling games globally",
            "🧭 Regional sales comparison per platform",
            "📈 Market evolution by platform over time",
            "📍 Regional genre preferences",
            "🔄 Yearly sales change per region",
            "🧮 Average sales per publisher",
            "🏆 Top 5 best-selling games per platform",

            # Merged dataset
            "🎮 Genres generating most global sales",
            "🎯 Effect of user rating on global sales",
            "🕹️ Platforms with most high-rated games",
            "📈 Trend of releases and sales over time",
            "🧍 Do highly wishlisted games lead to more sales?",
            "🎮 Genres with highest engagement but lowest sales",
            "🧠 Correlation between wishlist/backlogs and rating",
            "🏷️ User engagement across genres",
            "🎉 Top-performing Genre + Platform combinations",
            "🌐 Regional sales heatmap by genre"
        ]
    )

    # ---------------- Visualizations ----------------

    # 1️⃣ Top-rated games
    if question == "🌟 Top-rated games by user reviews" and 'Rating' in filtered.columns:
        top_games = filtered.nlargest(10, 'Rating')[['Title', 'Rating']]
        fig = px.bar(top_games, x='Rating', y='Title', orientation='h', color='Rating',
                     title="🌟 Top 10 Highest Rated Games", color_continuous_scale='Viridis')
        st.plotly_chart(fig, use_container_width=True)

    # 2️⃣ Developers with highest average ratings
    elif question == "🧑‍🤝‍🧑 Developers with highest average ratings" and 'Developer' in filtered.columns:
        dev_avg = filtered.groupby('Developer')['Rating'].mean().nlargest(10).reset_index()
        fig = px.bar(dev_avg, x='Rating', y='Developer', orientation='h', color='Rating',
                     title="🧑‍🤝‍🧑 Top Developers by Avg Rating", color_continuous_scale='Blues')
        st.plotly_chart(fig, use_container_width=True)

    # 3️⃣ Most common genres
    elif question == "🧩 Most common genres" and 'Genre' in filtered.columns:
        genre_count = filtered['Genre'].value_counts().reset_index()
        genre_count.columns = ['Genre', 'Count']
        fig = px.pie(genre_count, names='Genre', values='Count', title="🧩 Most Common Genres", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    # 4️⃣ Backlog vs Wishlist
    elif question == "⏳ Games with highest backlog vs wishlist" and {'Backlogs', 'Wishlist'}.issubset(filtered.columns):
        bl_wl = filtered.nlargest(10, 'Backlogs')[['Title', 'Backlogs', 'Wishlist']]
        fig = px.bar(bl_wl, x='Title', y=['Backlogs', 'Wishlist'], title="⏳ Backlogs vs Wishlist", barmode='group')
        st.plotly_chart(fig, use_container_width=True)

    # 5️⃣ Game release trend
    elif question == "🗓️ Game release trend across years" and 'Year' in filtered.columns:
        year_count = filtered.groupby('Year').size().reset_index(name='Count')
        fig = px.line(year_count, x='Year', y='Count', markers=True, title="🗓️ Game Release Trend Over Years")
        st.plotly_chart(fig, use_container_width=True)

    # 6️⃣ Distribution of user ratings
    elif question == "🔎 Distribution of user ratings" and 'Rating' in filtered.columns:
        fig = px.histogram(filtered, x='Rating', nbins=20, title="🔎 User Ratings Distribution", color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig, use_container_width=True)

    # 7️⃣ Top 10 most wishlisted games
    elif question == "🧑 Top 10 most wishlisted games" and 'Wishlist' in filtered.columns:
        wl = filtered.nlargest(10, 'Wishlist')[['Title', 'Wishlist']]
        fig = px.bar(wl, x='Wishlist', y='Title', orientation='h', color='Wishlist', color_continuous_scale='Reds',
                     title="🧑 Top 10 Most Wishlisted Games")
        st.plotly_chart(fig, use_container_width=True)

    # 8️⃣ Average plays per genre
    elif question == "🔬 Average number of plays per genre" and {'Genre', 'Plays'}.issubset(filtered.columns):
        plays = filtered.groupby('Genre')['Plays'].mean().reset_index()
        fig = px.bar(plays, x='Genre', y='Plays', color='Plays', color_continuous_scale='Tealgrn',
                     title="🔬 Avg Number of Plays per Genre")
        st.plotly_chart(fig, use_container_width=True)

    # 9️⃣ Region with highest sales
    elif question == "🌍 Region with highest game sales":
        region_cols = [c for c in filtered.columns if c.endswith('_Sales')]
        if region_cols:
            region_sales = filtered[region_cols].sum().reset_index()
            region_sales.columns = ['Region', 'Sales']
            fig = px.bar(region_sales, x='Region', y='Sales', color='Sales', title="🌍 Region with Highest Game Sales")
            st.plotly_chart(fig, use_container_width=True)

    # 🔝 10️⃣ Top 10 best-selling games globally
    elif question == "🔝 Top 10 best-selling games globally" and 'Global_Sales' in filtered.columns:
        best_sellers = filtered.nlargest(10, 'Global_Sales')[['Title', 'Global_Sales']]
        fig = px.bar(best_sellers, x='Global_Sales', y='Title', orientation='h', color='Global_Sales',
                     title="🔝 Top 10 Best-Selling Games Globally", color_continuous_scale='Sunset')
        st.plotly_chart(fig, use_container_width=True)

    # 11️⃣ Genres generating most global sales
    elif question == "🎮 Genres generating most global sales" and {'Genre', 'Global_Sales'}.issubset(filtered.columns):
        genre_sales = filtered.groupby('Genre')['Global_Sales'].sum().reset_index().sort_values('Global_Sales', ascending=False)
        fig = px.bar(genre_sales.head(15), x='Global_Sales', y='Genre', orientation='h', title="🎮 Genres Generating Most Global Sales")
        st.plotly_chart(fig, use_container_width=True)

    # 12️⃣ Effect of rating on sales
    elif question == "🎯 Effect of user rating on global sales" and {'Rating', 'Global_Sales'}.issubset(filtered.columns):
        fig = px.scatter(filtered, x='Rating', y='Global_Sales', color='Genre', title="🎯 Rating vs Global Sales", size='Global_Sales')
        st.plotly_chart(fig, use_container_width=True)

    # 🧠 Correlation heatmap
    elif question == "🧠 Correlation between wishlist/backlogs and rating" and {'Wishlist', 'Backlogs', 'Rating'}.issubset(filtered.columns):
        corr = filtered[['Wishlist', 'Backlogs', 'Rating']].corr()
        fig = px.imshow(corr, text_auto=True, title="🧠 Correlation: Wishlist, Backlogs, Rating", color_continuous_scale='RdBu_r')
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("📌 Visualization not available or missing columns for this dataset.")
