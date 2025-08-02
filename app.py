import json
import streamlit as st
import pandas as pd
import altair as alt

# Load BTC price JSON file
with open("btc_prices.json", "r") as f:
    btc_data = json.load(f)

# Convert to DataFrame
df_prices = pd.DataFrame(btc_data)
df_prices['Date'] = pd.to_datetime(df_prices['Date'])
df_prices = df_prices.sort_values('Date').reset_index(drop=True)

# ---- Streamlit UI ----
st.set_page_config(page_title="BTC DCA Simulator", layout="wide")
st.title("Bitcoin Daily Investment Tracker")

# User inputs
col_input1, col_input2 = st.columns(2)

with col_input1:
    days_back = st.number_input(
        "Enter number of days to go back (max 598):",
        min_value=1,
        max_value=598,
        value=120,
        step=1
    )

with col_input2:
    daily_investment = st.number_input(
        "Enter daily investment amount ($):",
        min_value=1,
        max_value=10000,
        value=100,
        step=10
    )

# --- Use the last N rows instead of calendar-based filtering ---
if len(df_prices) >= days_back:
    filtered_df = df_prices.tail(days_back).reset_index(drop=True)
else:
    st.warning(
        f"Only {len(df_prices)} days of data are available, "
        f"but you requested {days_back} days. Showing all available data."
    )
    filtered_df = df_prices.reset_index(drop=True)

# --- Portfolio Simulation ---
if filtered_df.empty:
    st.error("No data available to display.")
else:
    total_invested = 0
    btc_holding = 0
    portfolio_values = []
    total_invested_list = []
    btc_price_list = []

    for _, row in filtered_df.iterrows():
        price = row['Close']
        btc_bought = daily_investment / price
        btc_holding += btc_bought
        total_invested += daily_investment

        portfolio_value = btc_holding * price

        btc_price_list.append(price)
        portfolio_values.append(portfolio_value)
        total_invested_list.append(total_invested)

    # Create results DataFrame
    df_results = pd.DataFrame({
        'Date': filtered_df['Date'],
        'BTC Price': btc_price_list,
        'Portfolio Value': portfolio_values,
        'Total Invested': total_invested_list
    })

    # Add Day column starting from 1
    df_results.insert(0, "Day", range(1, len(df_results) + 1))

    # Format table for display
    def format_usd(x):
        return f"${x:,.2f}"

    df_display = df_results.copy()
    df_display['BTC Price'] = df_display['BTC Price'].map(format_usd)
    df_display['Portfolio Value'] = df_display['Portfolio Value'].map(format_usd)
    df_display['Total Invested'] = df_display['Total Invested'].map(format_usd)

    # Layout
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Portfolio Table")
        st.dataframe(df_display, use_container_width=True, height=600, hide_index=True)

    with col2:
        st.subheader("Portfolio Growth Over Time")

        # Use Day instead of Date for the x-axis
        chart_data = df_results.melt('Day', value_vars=['Portfolio Value', 'Total Invested'],
                                     var_name='Metric', value_name='Value')

        chart = alt.Chart(chart_data).mark_line().encode(
            x='Day:Q',
            y='Value:Q',
            color='Metric:N'
        ).properties(width=600, height=400)

        st.altair_chart(chart, use_container_width=True)
