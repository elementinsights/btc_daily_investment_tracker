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
st.title("Bitcoin Investment Tracker")

# --- User Inputs ---
col1, col2 = st.columns(2)

with col1:
    days_back = st.number_input(
        "Enter number of days to go back (max 598):",
        min_value=1,
        max_value=598,
        value=120,
        step=1
    )

with col2:
    investment_amount = st.number_input(
        "Investment amount per interval ($):",
        min_value=1,
        max_value=10000,
        value=100,
        step=10
    )

# --- Horizontal Radio Buttons ---
col_freq, col_yaxis = st.columns([1, 2])

with col_freq:
    investment_frequency = st.radio(
        "Investment frequency:",
        options=["Daily", "Weekly", "Monthly"],
        horizontal=True
    )

with col_yaxis:
    y_axis_mode = st.radio(
        "Y-axis chart mode:",
        options=["Portfolio Value", "% Gain"],
        horizontal=True
    )

# --- Filter DataFrame ---
if len(df_prices) >= days_back:
    filtered_df = df_prices.tail(days_back).reset_index(drop=True)
else:
    st.warning(
        f"Only {len(df_prices)} days of data are available, "
        f"but you requested {days_back} days. Showing all available data."
    )
    filtered_df = df_prices.reset_index(drop=True)

# --- Apply frequency slicing ---
if investment_frequency == "Daily":
    df_invest = filtered_df.copy()
elif investment_frequency == "Weekly":
    df_invest = filtered_df.iloc[::7].reset_index(drop=True)
elif investment_frequency == "Monthly":
    df_invest = filtered_df.iloc[::30].reset_index(drop=True)
else:
    df_invest = filtered_df.copy()

# --- Portfolio Simulation ---
if df_invest.empty:
    st.error("No data available to display.")
else:
    total_invested = 0
    btc_holding = 0
    portfolio_values = []
    total_invested_list = []
    btc_price_list = []
    pct_gains = []

    for _, row in df_invest.iterrows():
        price = row['Close']
        btc_bought = investment_amount / price
        btc_holding += btc_bought
        total_invested += investment_amount

        portfolio_value = btc_holding * price
        gain_pct = ((portfolio_value - total_invested) / total_invested) * 100

        btc_price_list.append(price)
        portfolio_values.append(portfolio_value)
        total_invested_list.append(total_invested)
        pct_gains.append(gain_pct)

    # Create results DataFrame
    df_results = pd.DataFrame({
        'Investment #': range(1, len(df_invest) + 1),
        'Date': df_invest['Date'],
        'BTC Price': btc_price_list,
        'Portfolio Value': portfolio_values,
        'Total Invested': total_invested_list,
        '% Gain': pct_gains
    })

    # --- Total Return Calculation ---
    final_value = portfolio_values[-1]
    final_invested = total_invested_list[-1]
    dollar_return = final_value - final_invested
    percent_return = (final_value / final_invested - 1) * 100

    # --- Format functions ---
    def format_usd(x): return f"${x:,.2f}"
    def format_pct(x): return f"{x:.2f}%"

    # --- Format table for display ---
    df_display = df_results.copy()
    df_display['BTC Price'] = df_display['BTC Price'].map(format_usd)
    df_display['Portfolio Value'] = df_display['Portfolio Value'].map(format_usd)
    df_display['Total Invested'] = df_display['Total Invested'].map(format_usd)
    df_display['% Gain'] = df_display['% Gain'].map(format_pct)

    # --- Chart Section ---
    st.subheader("Portfolio Performance Over Time")

    # ⏱ Weekly Investment Day Label
    if investment_frequency == "Weekly":
        weekday = df_invest['Date'].iloc[0].day_name()
        st.markdown(f"🗓️ **Weekly investments occur on:** `{weekday}s`")

    # 💹 Total Return Display
    if y_axis_mode == "Portfolio Value":
        st.markdown(f"💰 **Total Return:** `{format_usd(dollar_return)}`")
    else:
        st.markdown(f"📈 **Total Return:** `{format_pct(percent_return)}`")

    # --- Chart Generation ---
    if y_axis_mode == "Portfolio Value":
        chart_data = df_results.melt(
            id_vars=['Investment #'],
            value_vars=['Portfolio Value', 'Total Invested'],
            var_name='Metric',
            value_name='Value'
        )

        chart = alt.Chart(chart_data).mark_line().encode(
            x='Investment #:Q',
            y='Value:Q',
            color='Metric:N'
        ).properties(
            width='container',
            height=400
        )
    else:  # % Gain
        chart = alt.Chart(df_results).mark_line().encode(
            x='Investment #:Q',
            y=alt.Y('% Gain:Q', title='% Gain'),
            color=alt.value("green")
        ).properties(
            width='container',
            height=400
        )

    st.altair_chart(chart, use_container_width=True)

    # --- Table Below Chart ---
    st.subheader("Investment Table")
    st.dataframe(df_display, use_container_width=True, height=600, hide_index=True)
