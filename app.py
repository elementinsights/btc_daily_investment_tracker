import math
import json
from pathlib import Path
from typing import Optional, Union, Dict

import numpy as np
import pandas as pd
import streamlit as st

# ==============================
# App Config
# ==============================
st.set_page_config(
    page_title="DCA & SDCA Simulator",
    page_icon="📈",
    layout="wide",
)

# ==============================
# Data Discovery
# ==============================

def discover_price_files() -> Dict[str, Path]:
    """
    Find files matching '*_prices.json' in:
      - the same directory as this script
      - an optional 'data' subdirectory

    Returns a dict mapping SYMBOL -> Path, where SYMBOL is
    the part before the first underscore, uppercased.
    e.g. 'btc_prices.json' -> 'BTC'
    """
    here = Path(__file__).parent
    candidates = list(here.glob("*_prices.json"))

    data_dir = here / "data"
    if data_dir.exists():
        candidates += list(data_dir.glob("*_prices.json"))

    mapping: Dict[str, Path] = {}
    for p in candidates:
        stem = p.stem  # e.g., 'btc_prices'
        if "_" in stem:
            symbol = stem.split("_", 1)[0].upper()
        else:
            symbol = stem.upper()
        # prefer file closer to app (here) if duplicates exist
        if symbol not in mapping:
            mapping[symbol] = p
    return mapping

# ==============================
# Data Loading
# ==============================

@st.cache_data(show_spinner=False)
def load_prices_from_json(json_path: Union[str, Path]) -> pd.DataFrame:
    """
    Expected schema:
    [
      {"Date": "2023-12-11", "Close": 41237.43},
      ...
    ]
    """
    json_path = Path(json_path)
    if not json_path.exists():
        return pd.DataFrame(columns=["Date", "Close"])

    with open(json_path, "r") as f:
        raw = json.load(f)

    df = pd.DataFrame(raw)
    if "Date" not in df.columns or "Close" not in df.columns:
        return pd.DataFrame(columns=["Date", "Close"])

    df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_localize(None)
    df = df.sort_values("Date").dropna(subset=["Close"])
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna(subset=["Close"]).reset_index(drop=True)
    return df[["Date", "Close"]]

@st.cache_data(show_spinner=False)
def load_prices_from_symbol(symbol_to_path: Dict[str, Path], symbol: str) -> pd.DataFrame:
    if symbol not in symbol_to_path:
        return pd.DataFrame(columns=["Date", "Close"])
    return load_prices_from_json(symbol_to_path[symbol])

# ==============================
# SDCA / DCA Core
# ==============================

FREQ_LABELS = {"Daily": "D", "Weekly": "W-SUN", "Monthly": "M"}

def aggregate_prices(df: pd.DataFrame, frequency: str) -> pd.Series:
    """Aggregate close prices to the chosen frequency."""
    if df.empty:
        return pd.Series(dtype=float)
    s = df.set_index("Date")["Close"].sort_index()
    if frequency == "Daily":
        return s
    elif frequency == "Weekly":
        return s.resample("W-SUN").last().dropna()
    elif frequency == "Monthly":
        return s.resample("M").last().dropna()
    else:
        raise ValueError(f"Unknown frequency: {frequency}")

def simulate_standard_dca(prices: pd.Series, base: float) -> pd.DataFrame:
    rows = []
    cum_units = 0.0
    total_invested = 0.0
    for dt, price in prices.items():
        invest = base
        units = invest / price
        cum_units += units
        total_invested += invest
        rows.append({
            "Date": dt, "Price": float(price), "Invest": float(invest), "Units": float(units),
            "CumUnits": float(cum_units), "TotalInvested": float(total_invested),
            "Action": "base", "SkipsLeft": 0, "Mult": 1
        })
    out = pd.DataFrame(rows).sort_values("Date")
    out["PortfolioValue"] = out["CumUnits"] * out["Price"]
    out["ROI_%"] = np.where(out["TotalInvested"] > 0,
                            (out["PortfolioValue"] / out["TotalInvested"] - 1.0) * 100.0, 0.0)
    return out

def simulate_sdca(prices: pd.Series, base: float, threshold_pct: float,
                  max_k: Optional[int] = None) -> pd.DataFrame:
    """
    Special DCA logic:
    - If drop >= k * threshold from previous interval, invest (1+k)*base, skip k future intervals.
    """
    rows = []
    prev_price = None
    skip = 0
    cum_units = 0.0
    total_invested = 0.0
    g = threshold_pct / 100.0 if threshold_pct else 0.0

    for dt, price in prices.items():
        action = "base"
        mult = 1
        invest = 0.0

        if prev_price is None:
            invest = base
            action = "base (first)"
        elif skip > 0:
            action = f"skip ({skip} left)"
            skip -= 1
        else:
            change = (price - prev_price) / prev_price if prev_price != 0 else 0.0
            if change < 0 and g > 0:
                k = math.floor(abs(change) / g)
                if max_k is not None and max_k > 0:
                    k = min(k, max_k)
                if k > 0:
                    mult = 1 + k
                    invest = base * mult
                    skip = k
                    action = f"dip {k}× → buy {mult}×, skip {k}"
                else:
                    invest = base
            else:
                invest = base

        units = invest / price if invest > 0 else 0.0
        cum_units += units
        total_invested += invest

        rows.append({
            "Date": dt, "Price": float(price), "Invest": float(invest), "Units": float(units),
            "CumUnits": float(cum_units), "TotalInvested": float(total_invested),
            "Action": action, "SkipsLeft": skip, "Mult": mult
        })

        prev_price = price

    out = pd.DataFrame(rows).sort_values("Date")
    out["PortfolioValue"] = out["CumUnits"] * out["Price"]
    out["ROI_%"] = np.where(out["TotalInvested"] > 0,
                            (out["PortfolioValue"] / out["TotalInvested"] - 1.0) * 100.0, 0.0)
    return out

# ==============================
# UI
# ==============================

st.title("📈 DCA & SDCA Simulator")
st.caption("Simulate standard dollar-cost averaging or SDCA with skip windows on dips.")

with st.sidebar:
    st.header("Inputs")

    # --- Data Source dropdown ---
    symbol_to_path = discover_price_files()
    if not symbol_to_path:
        st.error(
            "No data files found. Place JSON files named like '*_prices.json' "
            "(e.g., btc_prices.json, eth_prices.json) next to the app or in a 'data/' folder."
        )
        df_prices = pd.DataFrame(columns=["Date", "Close"])
        symbol = None
    else:
        symbols = sorted(symbol_to_path.keys())
        symbol = st.selectbox("Data Source", symbols, index=0, help="Picks from *_prices.json files found.")
        df_prices = load_prices_from_symbol(symbol_to_path, symbol)

    # --- Date Range (slider) tied to the selected asset's data range ---
    if not df_prices.empty:
        min_dt = df_prices["Date"].min()
        max_dt = df_prices["Date"].max()

        date_range = st.slider(
            "Date Range",
            min_value=min_dt.date(),
            max_value=max_dt.date(),
            value=(min_dt.date(), max_dt.date()),
            format="YYYY-MM-DD",
        )
        start_date, end_date = date_range

        # Filter to selected range
        mask = (df_prices["Date"].dt.date >= start_date) & (df_prices["Date"].dt.date <= end_date)
        df_prices = df_prices.loc[mask].reset_index(drop=True)

    frequency = st.radio("Frequency", ["Daily", "Weekly", "Monthly"], horizontal=True)
    strategy = st.radio("Strategy", ["Standard DCA", "SDCA (Special DCA)"], horizontal=True)
    base_amount = st.number_input("Base investment ($)", min_value=1.0, value=100.0, step=10.0)

    if strategy.startswith("SDCA"):
        threshold = st.number_input("Dip threshold (%)", min_value=0.1, value=5.0, step=0.1)
        max_k = st.slider("Cap k (0 = no cap)", 0, 10, 0)
        max_k = None if max_k == 0 else int(max_k)
    else:
        threshold, max_k = 0.0, None

    run_button = st.button("Run Simulation", type="primary")

# ==============================
# Simulation & Results
# ==============================

if run_button:
    if df_prices.empty:
        st.stop()

    prices_series = aggregate_prices(df_prices, frequency)
    if prices_series.empty:
        st.warning("No prices in selected range.")
        st.stop()

    if strategy == "Standard DCA":
        sim = simulate_standard_dca(prices_series, base_amount)
    else:
        sim = simulate_sdca(prices_series, base_amount, threshold, max_k)

    last_row = sim.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Invested", f"${last_row['TotalInvested']:,.2f}")
    c2.metric("Final Value", f"${last_row['PortfolioValue']:,.2f}")
    c3.metric("ROI", f"{last_row['ROI_%']:.2f}%")
    c4.metric("Total Units", f"{last_row['CumUnits']:.8f}")

    st.subheader(f"{symbol or ''} Portfolio vs Invested")
    st.line_chart(sim.set_index("Date")[["PortfolioValue", "TotalInvested"]])

    st.subheader("Price & Investment per Interval")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.line_chart(sim.set_index("Date")[["Price"]])
    with col2:
        st.bar_chart(sim.set_index("Date")[["Invest"]])

    st.subheader("Transactions")
    pretty = sim.copy()
    pretty["Date"] = pretty["Date"].dt.strftime("%Y-%m-%d")
    st.dataframe(pretty[["Date", "Price", "Invest", "Units", "CumUnits",
                         "TotalInvested", "PortfolioValue", "ROI_%", "Action"]],
                 use_container_width=True, height=400)

    csv = pretty.to_csv(index=False).encode("utf-8")
    fname_symbol = (symbol or "data").lower()
    st.download_button("Download CSV", csv, f"simulation_{fname_symbol}.csv", "text/csv")
else:
    st.info("Set inputs and click **Run Simulation**.")
