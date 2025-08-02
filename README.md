# Bitcoin Daily Investment Tracker

This Streamlit app simulates a **daily dollar-cost averaging (DCA) investment strategy** for Bitcoin.  
It allows you to:

- Choose how many days back to simulate (up to 365).
- Set your daily investment amount (default $100).
- View a table showing your daily portfolio value.
- View a line chart showing portfolio growth and total invested over time.

---

## Features

- **Row-based filtering**: Always uses the last *N* data points regardless of missing calendar days.
- **Interactive inputs**: Adjust the number of days back and daily investment amount dynamically.
- **Outputs**:
  - A table with:
    - Day (1, 2, 3…)
    - Date
    - BTC Price
    - Portfolio Value
    - Total Invested
  - A chart with:
    - Portfolio Value
    - Total Invested (over Day)

---

## Requirements

- Python 3.8 or higher

## Required Python Packages

The app requires the following Python packages:

- **streamlit** – for building the interactive web app
- **pandas** – for handling and transforming the BTC price data
- **altair** – for creating interactive charts

You can install them with:

```bash
pip install streamlit pandas altair
````

## Running the App
```bash
streamlit run app.py
```