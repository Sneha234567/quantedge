import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add basic technical indicators to a price DataFrame.

    Expects columns: 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'
    """
    df = df.copy()

    # Simple moving averages
    df["SMA_20"] = df["Close"].rolling(window=20, min_periods=20).mean()
    df["SMA_50"] = df["Close"].rolling(window=50, min_periods=50).mean()
    # Exponential moving averages (for MACD)
    df["EMA_12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA_26"] = df["Close"].ewm(span=26, adjust=False).mean()

    # Daily returns
    df["Return"] = df["Close"].pct_change()

    # Rolling volatility (20-day standard deviation of returns)
    df["Volatility_20"] = df["Return"].rolling(window=20, min_periods=20).std()

    # Simple RSI (14-period) implementation
    window = 14
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    df["RSI_14"] = rsi

    # MACD (12/26 EMA) and signal (9 EMA of MACD)
    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    return df


if __name__ == "__main__":
    # Small self-test if you run this file directly
    import pathlib

    data_path = pathlib.Path("../data/AAPL.csv")
    if not data_path.exists():
        raise SystemExit("Run download_data.py first to create ../data/AAPL.csv")

    prices = pd.read_csv(data_path, parse_dates=["Date"], index_col="Date")
    prices = add_indicators(prices)
    print(prices.tail())




