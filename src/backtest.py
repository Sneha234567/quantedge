import pandas as pd


def backtest_long_only(
    df: pd.DataFrame,
    initial_capital: float = 10_000.0,
    trading_cost: float = 0.0,
    position_fraction: float = 1.0,
) -> pd.DataFrame:
    """
    Backtest a simple long-only strategy given a 'signal' column.

    Assumptions:
      - 'signal' is 1 when we are fully invested, 0 when in cash.
      - We use all available capital to buy shares when switching from 0 -> 1.
      - We sell all shares when switching from 1 -> 0.
      - 'Close' column is used as transaction price.

    Returns a DataFrame with additional columns:
      - 'cash'
      - 'shares'
      - 'portfolio_value'
    """
    if "signal" not in df.columns:
        raise ValueError("DataFrame must contain a 'signal' column.")

    df = df.copy()
    df["signal"] = df["signal"].fillna(0)

    cash = initial_capital
    shares = 0.0
    portfolio_values = []
    cash_list = []
    shares_list = []

    prev_signal = 0

    for date, row in df.iterrows():
        # Ensure we are working with a plain float price, not a pandas object/Series
        price = float(row["Close"])
        signal = int(float(row["signal"]))

        # Enter long position
        if prev_signal == 0 and signal == 1:
            # Buy as many shares as possible
            investable_cash = max(cash - trading_cost, 0) * max(min(position_fraction, 1.0), 0.0)
            new_shares = investable_cash / price if price > 0.0 else 0.0
            cash -= new_shares * price + trading_cost
            shares += new_shares

        # Exit long position
        elif prev_signal == 1 and signal == 0:
            if shares > 0:
                cash += shares * price - trading_cost
                shares = 0

        # Compute portfolio value
        portfolio_value = cash + shares * price

        cash_list.append(cash)
        shares_list.append(shares)
        portfolio_values.append(portfolio_value)

        prev_signal = signal

    df["cash"] = cash_list
    df["shares"] = shares_list
    df["portfolio_value"] = portfolio_values

    return df


def compute_performance_metrics(df: pd.DataFrame) -> dict:
    """
    Compute basic performance metrics from a backtested portfolio.
    Expects a 'portfolio_value' column indexed by date.
    """
    if "portfolio_value" not in df.columns:
        raise ValueError("DataFrame must contain 'portfolio_value' column.")

    pv = df["portfolio_value"]
    returns = pv.pct_change().dropna()

    total_return = pv.iloc[-1] / pv.iloc[0] - 1
    avg_daily_return = returns.mean()
    daily_vol = returns.std()
    sharpe = (avg_daily_return / daily_vol) * (252 ** 0.5) if daily_vol != 0 else 0.0

    running_max = pv.cummax()
    drawdown = (pv - running_max) / running_max
    max_drawdown = drawdown.min()

    metrics = {
        "start_value": float(pv.iloc[0]),
        "end_value": float(pv.iloc[-1]),
        "total_return": float(total_return),
        "avg_daily_return": float(avg_daily_return),
        "daily_volatility": float(daily_vol),
        "sharpe_ratio": float(sharpe),
        "max_drawdown": float(max_drawdown),
    }
    return metrics


if __name__ == "__main__":
    import pathlib
    from indicators import add_indicators
    from strategies import sma_cross_strategy

    data_path = pathlib.Path("../data/AAPL.csv")
    if not data_path.exists():
        raise SystemExit("Run download_data.py first to create ../data/AAPL.csv")

    prices = pd.read_csv(data_path, parse_dates=["Date"], index_col="Date")
    prices = add_indicators(prices)
    prices = sma_cross_strategy(prices)
    result = backtest_long_only(prices)
    metrics = compute_performance_metrics(result)
    print(metrics)




