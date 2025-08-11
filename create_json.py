import pandas as pd
import json

# Load your BTC CSV file (update the path to where your btc.csv is saved)
df = pd.read_csv("eth.csv")

# Normalize column names
df.columns = [c.strip().capitalize() for c in df.columns]

# Format the Date and Close columns
df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
df["Close"] = pd.to_numeric(df["Close"], errors="coerce").round(2)

# Drop any rows without Close values
df = df.dropna(subset=["Close"])

# Convert to list of dictionaries
btc_data = df.to_dict(orient="records")

# Save as JSON file
with open("eth_prices.json", "w") as f:
    json.dump(btc_data, f, indent=2)
