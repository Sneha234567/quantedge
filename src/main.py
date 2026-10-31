import pathlib

import matplotlib.pyplot as plt
import pandas as pd

from backtest import backtest_long_only, compute_performance_metrics
from indicators import add_indicators
from strategies import (
    buy_and_hold_strategy,
    macd_strategy,
    rsi_reversion_strategy,
    sma_cross_strategy,
)


def run_pipeline(
    symbol: str = "AAPL",
    csv_path: str = "../data/AAPL.csv",
    initial_capital: float = 10_000.0,
) -> None:
    """
    Full pipeline:
      1. Load historical data from CSV.
      2. Add indicators.
      3. Generate trading signals.
      4. Backtest portfolio.
      5. Print metrics and show plots.
    """
    path = pathlib.Path(csv_path)
    if not path.exists():
        raise SystemExit(
            f"{csv_path} not found. Run download_data.py first to download {symbol} data."
        )

    # 1) Load data from CSV exported by download_data.py.
    df = pd.read_csv(path)
    # Drop any stray header rows (e.g., ticker row) and ensure Date is parsed
    df = df[df["Date"].notna()]
    df["Date"] = pd.to_datetime(df["Date"])

    # Coerce price/volume columns to numeric
    price_cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    for col in price_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Close"])
    df = df.set_index("Date").sort_index()

    # 2) Add indicators
    df = add_indicators(df)

    # Containers for results
    strategies = {
        "Buy & Hold": buy_and_hold_strategy,
        "SMA Crossover": sma_cross_strategy,
        "RSI Reversion": rsi_reversion_strategy,
        "MACD": macd_strategy,
    }
    backtests = {}
    metrics_all = {}

    for name, strat_fn in strategies.items():
        df_strat = strat_fn(df)
        df_bt = backtest_long_only(df_strat, initial_capital=initial_capital)
        backtests[name] = df_bt
        metrics_all[name] = compute_performance_metrics(df_bt)

    print("=== Strategy comparison ===")
    for name, m in metrics_all.items():
        print(f"\n{name}:")
        for k, v in m.items():
            print(f"  {k:20s}: {v}")

    # 5) Basic plots for SMA crossover (as main example)
    sma_bt = backtests["SMA Crossover"]

    fig, (ax_price, ax_pv) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    ax_price.plot(sma_bt.index, sma_bt["Close"], label="Price")
    ax_price.plot(sma_bt.index, sma_bt["SMA_20"], label="SMA 20")
    ax_price.plot(sma_bt.index, sma_bt["SMA_50"], label="SMA 50")

    # Buy/sell markers (position changes)
    if "position_change" in sma_bt.columns:
        buys = sma_bt[sma_bt["position_change"] == 1]
        sells = sma_bt[sma_bt["position_change"] == -1]
        ax_price.scatter(buys.index, buys["Close"], marker="^", color="g", label="Buy")
        ax_price.scatter(sells.index, sells["Close"], marker="v", color="r", label="Sell")

    ax_price.set_title(f"{symbol} price and SMA crossover signals")
    ax_price.legend()

    for name, df_bt in backtests.items():
        ax_pv.plot(df_bt.index, df_bt["portfolio_value"], label=name)

    ax_pv.set_title("Portfolio value over time (strategy comparison)")
    ax_pv.legend()

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    run_pipeline()




