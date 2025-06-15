import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import requests
from textblob import TextBlob

# 1. Fetch stock data
def fetch_stock_data(symbol, start_date, end_date):
    df = yf.download(symbol, start=start_date, end=end_date)
    return df

# 2. Calculate indicators (RSI, MACD, Stochastic)
def calculate_indicators(df):
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    window_length = 14
    avg_gain = gain.rolling(window=window_length).mean()
    avg_loss = loss.rolling(window=window_length).mean()

    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    low14 = df['Low'].rolling(window=14).min()
    high14 = df['High'].rolling(window=14).max()
    df['%K'] = 100 * ((df['Close'] - low14) / (high14 - low14))
    df['%D'] = df['%K'].rolling(window=3).mean()

    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()

    return df

# 3. Detect crosses (Golden/Death Cross and MACD signal cross)
def detect_crosses(df):
    cross_type = "None"
    macd_signal_crossover = None

    if len(df) >= 200:
        if df['SMA50'].iloc[-2] < df['SMA200'].iloc[-2] and df['SMA50'].iloc[-1] > df['SMA200'].iloc[-1]:
            cross_type = "Golden Cross"
        elif df['SMA50'].iloc[-2] > df['SMA200'].iloc[-2] and df['SMA50'].iloc[-1] < df['SMA200'].iloc[-1]:
            cross_type = "Death Cross"

    if df['MACD'].iloc[-2] < df['Signal'].iloc[-2] and df['MACD'].iloc[-1] > df['Signal'].iloc[-1]:
        macd_signal_crossover = "Bullish Crossover"
    elif df['MACD'].iloc[-2] > df['Signal'].iloc[-2] and df['MACD'].iloc[-1] < df['Signal'].iloc[-1]:
        macd_signal_crossover = "Bearish Crossover"

    return cross_type, macd_signal_crossover

# 4. Fetch fundamentals from yfinance ticker
def fetch_fundamentals(ticker):
    info = ticker.info
    fundamentals = {
        'Market Cap': info.get('marketCap', 'N/A'),
        'PE Ratio': info.get('trailingPE', 'N/A'),
        'EPS': info.get('trailingEps', 'N/A'),
        'Dividend Yield': info.get('dividendYield', 'N/A'),
        '52 Week High': info.get('fiftyTwoWeekHigh', 'N/A'),
        '52 Week Low': info.get('fiftyTwoWeekLow', 'N/A'),
    }
    return fundamentals

# 5. Plot stock price and SMA lines
def plot_stock(df, symbol):
    plt.figure(figsize=(14,7))
    plt.plot(df.index, df['Close'], label='Close Price')
    plt.plot(df.index, df['SMA50'], label='SMA 50')
    plt.plot(df.index, df['SMA200'], label='SMA 200')
    plt.title(f"{symbol} Price Chart")
    plt.xlabel('Date')
    plt.ylabel('Price ($)')
    plt.legend()
    plt.grid()
    st.pyplot(plt)
    plt.clf()

# 6. Fetch news headlines using NewsAPI
def fetch_newsapi_news(symbol, max_articles=7):
    api_key = "YOUR_NEWSAPI_KEY"  # Replace this
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={symbol}&"
        f"pageSize={max_articles}&"
        f"sortBy=publishedAt&"
        f"language=en&"
        f"apiKey={api_key}"
    )
    response = requests.get(url)
    if response.status_code != 200:
        return [], []
    data = response.json()
    articles = data.get("articles", [])
    headlines = [article["title"] for article in articles]
    links = [article["url"] for article in articles]
    return headlines, links

# 7. Sentiment analysis on news headlines
def sentiment_analysis(headlines):
    if not headlines:
        return None, "No headlines to analyze."
    polarity_scores = [TextBlob(headline).sentiment.polarity for headline in headlines]
    avg_sentiment = np.mean(polarity_scores)
    if avg_sentiment > 0.05:
        summary = "Positive"
    elif avg_sentiment < -0.05:
        summary = "Negative"
    else:
        summary = "Neutral"
    return avg_sentiment, summary

# 8. Summary report generator
def summary_report(fundamentals, avg_sentiment, technical_decision, decision_notes):
    fa_msgs = []
    if fundamentals.get('PE Ratio') != 'N/A' and fundamentals['PE Ratio'] < 15:
        fa_msgs.append("PE Ratio suggests the stock might be undervalued.")
    else:
        fa_msgs.append("PE Ratio is average or high.")

    qa_msg = f"News sentiment is {('positive' if avg_sentiment and avg_sentiment > 0 else 'neutral/negative')}."
    ta_msg = f"Technical analysis suggests: {technical_decision}."
    overall = "BUY" if technical_decision == "BUY" and avg_sentiment and avg_sentiment > 0 else "HOLD/WAIT"

    return fa_msgs, qa_msg, ta_msg, decision_notes, overall

# Main Streamlit app
def main():
    st.title("📈 Comprehensive Stock Analysis & News Dashboard")

    symbol = st.text_input("Enter Stock Symbol (e.g., AAPL)").upper().strip()

    if st.button("Analyze"):
        if not symbol:
            st.warning("Please enter a valid stock symbol.")
            return

        start_date = "2023-01-01"
        end_date = datetime.datetime.today().strftime('%Y-%m-%d')

        with st.spinner("Downloading stock data..."):
            df = fetch_stock_data(symbol, start_date, end_date)

        if df.empty:
            st.error(f"No data found for symbol '{symbol}'. Please check the symbol and try again.")
            return

        df = calculate_indicators(df)
        cross_type, macd_signal_crossover = detect_crosses(df)

        # Simple technical decision logic
        technical_decision = "HOLD"
        decision_notes = []
        if cross_type == "Golden Cross" or macd_signal_crossover == "Bullish Crossover":
            technical_decision = "BUY"
            decision_notes.append("Bullish technical signals detected.")
        elif cross_type == "Death Cross" or macd_signal_crossover == "Bearish Crossover":
            technical_decision = "SELL"
            decision_notes.append("Bearish technical signals detected.")
        else:
            decision_notes.append("No strong technical signals detected.")

        ticker = yf.Ticker(symbol)
        fundamentals = fetch_fundamentals(ticker)

        st.subheader(f"{symbol} Price Chart with Indicators")
        plot_stock(df, symbol)

        st.subheader("Technical Indicator Summary")
        st.write(f"**Golden/Death Cross:** {cross_type}")
        st.write(f"**MACD Signal:** {macd_signal_crossover if macd_signal_crossover else 'No recent crossover'}")
        st.write(f"**RSI:** {df['RSI'].iloc[-1]:.2f}")
        st.write(f"**Stochastic %K:** {df['%K'].iloc[-1]:.2f}, %D: {df['%D'].iloc[-1]:.2f}")

        st.subheader("Fundamental Data")
        for key, val in fundamentals.items():
            st.write(f"- {key}: {val}")

        st.subheader("Recent News Headlines (NewsAPI)")
        headlines, links = fetch_newsapi_news(symbol)
        if headlines:
            for i, (headline, link) in enumerate(zip(headlines, links), 1):
                st.markdown(f"{i}. [{headline}]({link})")
        else:
            st.write("No recent news found from NewsAPI.")

        avg_sentiment, sentiment_summary = sentiment_analysis(headlines)
        st.subheader("News Sentiment Analysis")
        if avg_sentiment is not None:
            st.write(f"Sentiment: **{sentiment_summary}** (Average polarity score: {avg_sentiment:.2f})")
        else:
            st.write("No news sentiment data available.")

        fa_msgs, qa_msg, ta_msg, decision_notes, overall = summary_report(fundamentals, avg_sentiment, technical_decision, decision_notes)

        st.header("📊 Summary Dashboard")
        st.subheader("Fundamental Analysis")
        for msg in fa_msgs:
            st.write("- " + msg)

        st.subheader("Qualitative Analysis (News Sentiment)")
        st.write(qa_msg)

        st.subheader("Technical Analysis")
        st.write(ta_msg)
        for note in decision_notes:
            st.write("- " + note)

        st.markdown(f"### Overall Recommendation: {overall}")

        # Option trading suggestion
        if technical_decision == "BUY" and avg_sentiment and avg_sentiment > 0.05:
            st.success("🎯 Option Trading Suggestion: Good time to consider BUYING CALL OPTIONS based on bullish technical signals and positive news sentiment.")
        else:
            st.info("🎯 Option Trading Suggestion: Not a strong signal to buy call options at this time.")

if __name__ == "__main__":
    main()
