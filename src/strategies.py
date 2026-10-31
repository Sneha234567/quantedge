import pandas as pd


def sma_cross_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simple moving average crossover strategy.

    Uses SMA_20 and SMA_50 columns (must be precomputed).
    Signal logic (long-only):
      - 1 when SMA_20 > SMA_50  (in the market)
      - 0 otherwise             (out of the market)
    """
    if "SMA_20" not in df.columns or "SMA_50" not in df.columns:
        raise ValueError("DataFrame must contain 'SMA_20' and 'SMA_50' columns.")

    df = df.copy()
    df["signal"] = 0
    df.loc[df["SMA_20"] > df["SMA_50"], "signal"] = 1

    # Optionally, you can compute trades (changes in position)
    df["position_change"] = df["signal"].diff().fillna(0)

    return df


def macd_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """
    MACD strategy using MACD and MACD_signal columns (must be precomputed).
    Signal logic (long-only):
      - 1 when MACD crosses above MACD_signal (bullish)
      - 0 when MACD crosses below MACD_signal (bearish)
    """
    if "MACD" not in df.columns or "MACD_signal" not in df.columns:
        raise ValueError("DataFrame must contain 'MACD' and 'MACD_signal' columns.")

    df = df.copy()
    df["signal"] = 0
    cross_up = (df["MACD"] > df["MACD_signal"]) & (df["MACD"].shift(1) <= df["MACD_signal"].shift(1))
    cross_dn = (df["MACD"] < df["MACD_signal"]) & (df["MACD"].shift(1) >= df["MACD_signal"].shift(1))

    df.loc[cross_up, "signal"] = 1
    df.loc[cross_dn, "signal"] = 0
    df["signal"] = df["signal"].ffill().fillna(0)
    df["position_change"] = df["signal"].diff().fillna(0)
    return df


def rsi_reversion_strategy(
    df: pd.DataFrame,
    lower: float = 30.0,
    upper: float = 70.0,
) -> pd.DataFrame:
    """
    RSI-based mean-reversion strategy.

    Uses RSI_14 column (must be precomputed).
    Signal logic (long-only):
      - 1 when RSI_14 < lower  (oversold -> buy)
      - 0 when RSI_14 > upper  (overbought -> exit)
      - otherwise keep previous position
    """
    if "RSI_14" not in df.columns:
        raise ValueError("DataFrame must contain 'RSI_14' column.")

    df = df.copy()

    # Start flat
    signals = []
    current_pos = 0
    for rsi in df["RSI_14"]:
        if pd.isna(rsi):
            signals.append(0)
            current_pos = 0
            continue

        if current_pos == 0 and rsi < lower:
            current_pos = 1
        elif current_pos == 1 and rsi > upper:
            current_pos = 0

        signals.append(current_pos)

    df["signal"] = signals
    df["position_change"] = df["signal"].diff().fillna(0)

    return df


def buy_and_hold_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Buy-and-hold baseline: always fully invested after the first day.
    """
    df = df.copy()
    df["signal"] = 1
    df.iloc[0, df.columns.get_loc("signal")] = 0  # start in cash on first day
    df["signal"] = df["signal"].ffill()
    df["position_change"] = df["signal"].diff().fillna(0)
    return df


if __name__ == "__main__":
    import pathlib
    from indicators import add_indicators

    data_path = pathlib.Path("../data/AAPL.csv")
    if not data_path.exists():
        raise SystemExit("Run download_data.py first to create ../data/AAPL.csv")

    prices = pd.read_csv(data_path, parse_dates=["Date"], index_col="Date")
    prices = add_indicators(prices)
    prices = sma_cross_strategy(prices)
    print(prices[["Close", "SMA_20", "SMA_50", "signal"]].tail())




