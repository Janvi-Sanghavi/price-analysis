import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ------------  Paths --------------
PROJECT = Path(__file__).parent.parent  # the main project folder
RAW = PROJECT / "raw_data"
CHARTS = PROJECT / "python" / "charts"
CHARTS.mkdir(exist_ok = True)  # creates a folder for the charts


# ------------ 1. Load & combine all CSVs ---------------
files = list(RAW.glob("*.csv"))
print("Files found:", len(files))

df = pd.concat([pd.read_csv(f) for f in files], ignore_index = True)
print("Rows: ", len(df))
print(df.head())
print(df.dtypes)

#------------- 2. Clean ---------------
# 2a. Drop the column we don't need
df = df.drop(columns = ["Commodity_Code"])

# 2b. Trim spaces in all text columns
text_cols = ["Commodity", "District", "Grade", "Market", "State", "Variety"]
for col in text_cols:
    df[col] = df[col].str.strip()

# 2c. Standardise city names
df["District"] = df["District"].replace("Bangalore", "Bengaluru")

# 2d. Convert text date -> real date (DD/MM/YYYY, Indian format)
df["Arrival_Date"] = pd.to_datetime(df["Arrival_Date"], format = "%d/%m/%Y")

# 2e. Remove exact duplicate rows
before = len(df)
df = df.drop_duplicates()
print("Duplicates removed:", before - len(df))


# -------------------- 3. Quality Flag (Same rules as excel) -----------------------
def quality_flag(row):
    if (row['Min_Price'] > row['Max_Price']) or row ['Modal_Price'] < row ['Min_Price'] or row['Modal_Price'] > row['Max_Price']:
        return "Logic error"
    if row['Modal_Price'] < 50:
        return "Too Low"
    limits = {"Onion": 15000, "Tomato": 16000, "Potato": 6000}
    if row["Modal_Price"] > limits[row["Commodity"]]:
        return "Outlier"
    return "OK"

df["Quality_Flag"] = df.apply(quality_flag, axis = 1)
print(df["Quality_Flag"].value_counts())

df = df[df["Quality_Flag"] == "OK"].drop(columns = ["Quality_Flag"])
print("Clean rows:", len(df))


# -------------------- 4. New Columns -----------------------------
df["Year"] = df["Arrival_Date"].dt.year
df["Month"] = df["Arrival_Date"].dt.month
df["Month_Name"] = df["Arrival_Date"].dt.strftime("%b")   # Jan, Feb....
df["Price_per_kg"] = df["Modal_Price"] / 100
df["Price_Spread"] = df["Max_Price"] - df["Min_Price"]

# Lookup: Season (Same as Excel season_map + XLOOKUP)
season_map = {
    1: "Winter",
    2: "Winter",
    3: "Summer",
    4: "Summer",
    5: "Summer",
    6: "Monsoon",
    7: "Monsoon",
    8: "Monsoon",
    9: "Monsoon",
    10: "Post-Monsoon",
    11: "Post-Monsoon",
    12: "Winter"
}
df["Season"] = df["Month"].map(season_map)

# Lookup: Market type
df["Market_Type"] = df["District"].map({"Nashik": "Producer", "Pune": "Producer",
                                        "Delhi": "Consumer", "Bengaluru": "Consumer"})


# Save the clean dataset
df.to_csv(PROJECT / "python" / "mandi_prices_clean_python.csv", index = False)
print(df[["Arrival_Date", "Commodity", "District", "Price_per_kg", "Season"]].head())

# -------------------- 5. Charts ------------------------------------
sns.set_theme(style = "whitegrid")
recent = df[df["Year"] >= 2022]

season = recent.groupby(["Month", "Commodity"])["Price_per_kg"].mean().reset_index()

plt.figure(figsize = (10, 5))
sns.lineplot(data = season, x = "Month", y = "Price_per_kg", hue = "Commodity", marker = "o")
plt.title("Seasonality: average price by month (2022 - 2026)")
plt.xlabel("Month")
plt.ylabel("Price per kg")
plt.xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
plt.tight_layout()
plt.savefig(CHARTS / "01_seasonality.png", dpi = 150)
plt.close()
print("Saved chart 1")

# Chart 2: Yearly Trend
yearly = df.groupby(["Year", "Commodity"])["Price_per_kg"].mean().reset_index()
sns.lineplot(data = yearly, x = "Year", y = "Price_per_kg", hue = "Commodity")
plt.title("Yearly avergae price, 2001 - 2026")
plt.ylabel("₹ per kg")
plt.tight_layout()
plt.savefig(CHARTS / "02_yearly_trend.png", dpi = 150)
plt.close()
print("Saved chart 2")

# Chart 3: City comparison (2022 - 2025, complete data for all cities)
city_df = df[(df["Year"] >= 2022) & (df["Year"] <= 2025)]
city = city_df.groupby(["District", "Commodity"])["Price_per_kg"].mean().reset_index()
plt.figure(figsize = (10, 5))
sns.barplot(data = city, x = "District", y = "Price_per_kg", hue = "Commodity")
plt.title("Average price by city, 2022 - 2025")
plt.ylabel("₹ per kg")
plt.xlabel("")
plt.tight_layout()
plt.savefig(CHARTS / "03_city_comparison.png", dpi = 150)
plt.close()
print("Saved chart 3")

# Chart 4: 2023 tomato crisis, month by month
tomato23 = df[(df["Commodity"] == "Tomato") & (df["Year"] == 2023)]
monthly = tomato23.groupby("Month")["Price_per_kg"].mean()
plt.figure(figsize = (10, 5))
plt.bar(monthly.index, monthly.values, color = "#C0392B")
plt.title("2023 tomato crisis: Average price by month")
plt.ylabel("₹ per kg")
plt.xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
plt.tight_layout()
plt.savefig(CHARTS / "04_tomato_crisis_2023.png", dpi = 150)
plt.close()
print("Saved chart 4")

# ------------ 6. Statistics -------------------
print("\n==== A. Mean, Median, Voltality (2022 - 2026) ====")
stats = recent.groupby("Commodity")["Price_per_kg"].agg(["mean", "median", "std"]).round(1)
stats["CV_%"] = (stats["std"] / stats["mean"] * 100).round(0)
print(stats.sort_values("CV_%", ascending = False))

print("\n=== B. Does Nashik onion price lead Delhi? ====")
onion = recent[recent["Commodity"] == "Onion"]
weekly = (onion.groupby(["District", pd.Grouper(key = "Arrival_Date", freq = "W")])["Price_per_kg"].mean().unstack("District"))
for lag in range(0, 5):
    corr = weekly["Nashik"].shift(lag).corr(weekly["Delhi"])
    print(f"Nashik {lag} week(s) earlier vs Delhi: correlation = {corr: .3f}")