import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
import pandasql as ps  # to run SQL queries on pandas dataframe

# Page config
st.set_page_config(page_title="OLA Dashboard", page_icon="🚖", layout="wide")

# Load Dataset
@st.cache_data
def load_data():
    df = pd.read_csv("OLA_DataSet.csv")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df.columns = df.columns.str.strip()  # clean col names
    return df

df = load_data()

# Sidebar Navigation
page = st.sidebar.radio("📂 Select Page", ["Dashboard", "SQL QUERY", "Project Documentation & Deployment"])

# -----------------------------------
# DASHBOARD PAGE
# -----------------------------------
if page == "Dashboard":
    st.title("🚖 OLA Rides Dashboard")
    st.markdown("### Interactive Analysis of Ola Rides — Status, Revenue, Locations & More")

    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    vehicle = st.sidebar.multiselect("Select Vehicle Type", df["Vehicle_Type"].unique())
    payment = st.sidebar.multiselect("Select Payment Method", df["Payment_Method"].unique())
    status = st.sidebar.multiselect("Select Ride Status", df["Booking_Status"].unique())

    # Apply filters
    filtered_df = df.copy()
    if vehicle:
        filtered_df = filtered_df[filtered_df["Vehicle_Type"].isin(vehicle)]
    if payment:
        filtered_df = filtered_df[filtered_df["Payment_Method"].isin(payment)]
    if status:
        filtered_df = filtered_df[filtered_df["Booking_Status"].isin(status)]

    # KPIs row
    total_rides = len(filtered_df)
    success_rides = len(filtered_df[filtered_df["Booking_Status"] == "Success"])
    success_rate = round((success_rides / total_rides) * 100, 2) if total_rides > 0 else 0
    total_revenue = filtered_df["Booking_Value"].sum()
    avg_fare = round(filtered_df["Booking_Value"].mean(), 2)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Rides", total_rides)
    kpi2.metric("Success Rate", f"{success_rate}%")
    kpi3.metric("Total Revenue", f"₹{total_revenue:,.0f}")
    kpi4.metric("Average Fare", f"₹{avg_fare}")

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Ride Status Distribution")
        fig1 = px.histogram(filtered_df, x="Booking_Status", color="Booking_Status", text_auto=True)
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.subheader("💳 Payment Method Share")
        fig2 = px.pie(filtered_df, names="Payment_Method", title="Payment Method Distribution")
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("💰 Top Revenue Pickup Locations")
        revenue_by_pickup = (
            filtered_df.groupby("Pickup_Location")["Booking_Value"]
            .sum().nlargest(10).reset_index()
        )
        revenue_by_pickup.columns = ["Pickup_Location", "Revenue"]
        fig_rev = px.bar(
            revenue_by_pickup, x="Revenue", y="Pickup_Location", orientation="h",
            title="Top 10 Revenue Pickup Locations", text_auto=True,
            color_discrete_sequence=["#FFD700"]
        )
        st.plotly_chart(fig_rev, use_container_width=True)

    with col4:
        st.subheader("📍 Top Pickup Locations")
        top_pickups = filtered_df["Pickup_Location"].value_counts().head(10).reset_index()
        top_pickups.columns = ["Pickup_Location", "Count"]
        fig4 = px.bar(
            top_pickups, x="Count", y="Pickup_Location", orientation="h",
            title="Top 10 Pickup Locations", text_auto=True,
            color_discrete_sequence=["#32CD32"]
        )
        st.plotly_chart(fig4, use_container_width=True)

    st.subheader("⏰ Rides by Hour of Day")
    filtered_df["Hour"] = filtered_df["Date"].dt.hour
    rides_by_hour = filtered_df.groupby("Hour")["Booking_ID"].count().reset_index()
    fig7 = px.density_heatmap(rides_by_hour, x="Hour", y="Booking_ID",
                              nbinsx=24, title="Ride Frequency by Hour",
                              color_continuous_scale="Viridis")
    st.plotly_chart(fig7, use_container_width=True)

    st.subheader("📈 Distance vs Fare Correlation")
    fig5 = px.scatter(filtered_df, x="Ride_Distance", y="Booking_Value",
                      color="Vehicle_Type", size="Booking_Value",
                      title="Distance vs Fare")
    st.plotly_chart(fig5, use_container_width=True)

# -----------------------------------
# SQL QUERY PAGE
# -----------------------------------
elif page == "SQL QUERY":
    st.title("🗄 SQL Query Explorer")
    st.markdown("### Run SQL queries on Ola dataset (via pandasql).")

    # Predefined SQL queries
    sql_queries = {
        "1. Retrieve all successful bookings": "SELECT * FROM df WHERE Booking_Status = 'Success'",
        "2. Average ride distance per vehicle type": "SELECT Vehicle_Type, AVG(Ride_Distance) as Avg_Distance FROM df GROUP BY Vehicle_Type",
        "3. Total cancelled rides by customers": "SELECT COUNT(*) as Cancelled_Rides FROM df WHERE Booking_Status = 'Cancelled by Customer'",
        "4. Top 5 customers with most rides": "SELECT Customer_ID, COUNT(*) as Ride_Count FROM df GROUP BY Customer_ID ORDER BY Ride_Count DESC LIMIT 5",
        "5. Rides cancelled by drivers (personal & car issues)": "SELECT COUNT(*) as Driver_Cancellations FROM df WHERE Booking_Status IN ('Cancelled - Personal', 'Cancelled - Car Issue')",
        "6. Rides paid using UPI": "SELECT * FROM df WHERE Payment_Method = 'UPI'",
        "7. Average customer rating per vehicle type": "SELECT Vehicle_Type, AVG(Customer_Rating) as Avg_Rating FROM df GROUP BY Vehicle_Type",
        "8. Total booking value of successful rides": "SELECT SUM(Booking_Value) as Total_Success_Revenue FROM df WHERE Booking_Status = 'Success'",
        "9. Incomplete rides with reason": "SELECT Booking_ID, Booking_Status FROM df WHERE Booking_Status LIKE 'Incomplete%'"
    }

    selected_query = st.selectbox("Choose a SQL Question:", list(sql_queries.keys()))
    query = sql_queries[selected_query]

    st.code(query, language="sql")
    result = ps.sqldf(query, locals())
    st.dataframe(result, use_container_width=True)

# -----------------------------------
# DOCUMENTATION PAGE
# -----------------------------------
elif page == "Project Documentation & Deployment":
    st.title("📑 Project Documentation & Deployment")
    st.markdown("""
    ### Project Overview
    This OLA Dashboard provides insights into ride bookings, revenue, cancellations, and customer/driver behavior.

    ### Key Features
    - KPI cards for quick performance overview  
    - Interactive charts (status, revenue, payments, locations)  
    - SQL Query Explorer to run analysis in SQL format  

    ### Deployment
    - The app can be deployed on **Streamlit Cloud / Heroku / AWS EC2**  
    - Dataset (`OLA_DataSet.csv`) should be included in the repository  
    - Install dependencies: `pip install streamlit plotly pandas pandasql pillow`  
    - Run app: `streamlit run app.py`  

    ### Business Insights
    - Most cancellations happen from customers rather than drivers  
    - UPI & Wallet payments dominate digital transactions  
    - Prime Sedan generates the highest average revenue per ride  
    - Evening hours show peak demand trends  
    """)
