import streamlit as st
import yfinance as yf
import pandas as pd

def safe_div(a, b):
    try:
        return a / b
    except:
        return None

st.title("📊 5-Year Buffett-Style Stock Performance Analyzer with Valuation Ratios and 10-Year Price Chart")

ticker = st.text_input("Enter ticker:", "AAPL").upper()
if not ticker:
    st.stop()

stock = yf.Ticker(ticker)

# --- Financials (5 Years) ---
hist = stock.history(period="5y")
year_ends = hist.resample('Y').last()

financials = stock.financials.T
balance_sheet = stock.balance_sheet.T
cashflow = stock.cashflow.T

years = financials.index[:5]

results = []

for i, year in enumerate(years):
    try:
        net_income = financials.loc[year].get('Net Income', None)
        total_debt = balance_sheet.loc[year].get('Total Debt', None)
        equity = balance_sheet.loc[year].get('Total Stockholder Equity', None)
        total_revenue = financials.loc[year].get('Total Revenue', None)
        cash_from_ops = cashflow.loc[year].get('Total Cash From Operating Activities', None)
        capex = cashflow.loc[year].get('Capital Expenditures', None)

        fcf = None
        if cash_from_ops is not None and capex is not None:
            fcf = cash_from_ops + capex  # Capex is negative

        roe = safe_div(net_income, equity) * 100 if net_income and equity and equity != 0 else None
        debt_to_equity = safe_div(total_debt, equity) if total_debt and equity and equity != 0 else None
        profit_margin = safe_div(net_income, total_revenue) * 100 if net_income and total_revenue else None

        price_date = year_ends.index[i] if i < len(year_ends) else None
        price = year_ends.loc[price_date]['Close'] if price_date is not None else None

        shares_outstanding = stock.info.get('sharesOutstanding', None)
        market_cap = price * shares_outstanding if price and shares_outstanding else None

        pe = safe_div(price, safe_div(net_income, shares_outstanding)) if net_income and shares_outstanding and price else None
        pb = safe_div(price, safe_div(equity, shares_outstanding)) if equity and shares_outstanding and price else None
        ps = safe_div(price, safe_div(total_revenue, shares_outstanding)) if total_revenue and shares_outstanding and price else None
        pfcf = safe_div(price, safe_div(fcf, shares_outstanding)) if fcf and shares_outstanding and price else None

        results.append({
            "Year": year.year if hasattr(year, 'year') else str(year),
            "Net Income": net_income,
            "Total Debt": total_debt,
            "Equity": equity,
            "Free Cash Flow": fcf,
            "ROE (%)": roe,
            "Debt/Equity": debt_to_equity,
            "Profit Margin (%)": profit_margin,
            "P/E": pe,
            "P/B": pb,
            "P/S": ps,
            "P/FCF": pfcf
        })
    except Exception:
        continue

df = pd.DataFrame(results)

def fmt_currency(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return f"${x:,.0f}"

def fmt_percent(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return f"{x:.2f}%"

def fmt_float(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return f"{x:.2f}"

st.subheader(f"{ticker} Financials + Valuation Ratios (Last 5 Years)")
st.dataframe(df.style.format({
    "Net Income": fmt_currency,
    "Total Debt": fmt_currency,
    "Equity": fmt_currency,
    "Free Cash Flow": fmt_currency,
    "ROE (%)": fmt_percent,
    "Debt/Equity": fmt_float,
    "Profit Margin (%)": fmt_percent,
    "P/E": fmt_float,
    "P/B": fmt_float,
    "P/S": fmt_float,
    "P/FCF": fmt_float
}))

# Buffett-style evaluation
good_years = 0
total_years = len(df)

for _, row in df.iterrows():
    if row["Net Income"] and row["Net Income"] > 0 \
       and row["ROE (%)"] and row["ROE (%)"] > 15 \
       and row["Profit Margin (%)"] and row["Profit Margin (%)"] > 10 \
       and row["Debt/Equity"] and row["Debt/Equity"] < 0.5 \
       and row["P/E"] and row["P/E"] < 20 \
       and row["P/B"] and row["P/B"] < 3 \
       and row["P/S"] and row["P/S"] < 4 \
       and (row["P/FCF"] is None or row["P/FCF"] < 20):
        good_years += 1

if total_years == 0:
    st.error("Insufficient data to analyze.")
else:
    if good_years >= total_years * 0.6:
        st.success(f"✅ {ticker} has performed well in the last {total_years} years based on Buffett's criteria.")
    else:
        st.warning(f"⚠️ {ticker} shows mixed or weak performance in the last {total_years} years.")

# --- Interpretation ---
st.subheader("📋 Interpretation")

if total_years == 0:
    st.write("No sufficient financial data to provide interpretation.")
else:
    st.markdown(f"""
    **Summary:**

    - **Positive Years:** {good_years} out of {total_years} years met Buffett's criteria for strong financial health and valuation.
    - **Net Income:** The company has {'mostly positive' if good_years >= total_years * 0.6 else 'variable or negative'} net income trends.
    - **Return on Equity (ROE):** The company shows {'strong' if good_years >= total_years * 0.6 else 'inconsistent'} ROE performance (target >15%).
    - **Profit Margin:** Profit margins are {'healthy' if good_years >= total_years * 0.6 else 'below ideal'} (target >10%).
    - **Debt/Equity:** The company maintains a {'low' if good_years >= total_years * 0.6 else 'relatively high'} debt level relative to equity (target <0.5).
    - **Valuation Ratios (P/E, P/B, P/S, P/FCF):** Valuation is {'attractive' if good_years >= total_years * 0.6 else 'mixed or high'} based on Buffett’s thresholds.

    > **Overall:** This analysis suggests the company has {'strong fundamentals and valuation' if good_years >= total_years * 0.6 else 'some weaknesses or risks'} in the recent 5 years.
    """)

# --- 10-Year Price Movement Chart ---
st.subheader(f"📈 {ticker} 10-Year Price Movement")

hist_10y = stock.history(period="10y")

if hist_10y.empty:
    st.write("No 10-year price data available.")
else:
    price_10y = hist_10y['Close']
    st.line_chart(price_10y)

    # Add price interpretation below the chart
    start_price = price_10y.iloc[0]
    end_price = price_10y.iloc[-1]
    change_pct = ((end_price - start_price) / start_price) * 100

    st.markdown(f"""
    **Price Movement Interpretation:**

    - Starting Price (10 years ago): ${start_price:,.2f}
    - Current Price: ${end_price:,.2f}
    - Total Change: {change_pct:.2f}%

    {'📈 The stock has shown significant growth over the last 10 years.' if change_pct > 20 else
     '⚠️ The stock has shown limited growth or decline over the last 10 years.'}
    """)