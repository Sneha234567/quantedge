import pandas as pd
import yfinance as yf
from pathlib import Path


def download_stock(symbol: str, start: str, end: str, filename: str) -> None:
    """
    Download historical stock data using yfinance and save to CSV.

    :param symbol: Ticker symbol, e.g. "AAPL"
    :param start: Start date as "YYYY-MM-DD"
    :param end: End date as "YYYY-MM-DD"
    :param filename: Path to CSV file where data will be saved
    """
    print(f"Downloading data for {symbol} from {start} to {end} ...")
    data = yf.download(symbol, start=start, end=end, progress=False, group_by="column")

    if data is None or data.empty:
        raise SystemExit(f"No data downloaded for {symbol}. Check symbol or network.")

    # Flatten possible multi-index columns (e.g., ("Close", "AAPL") -> "Close")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [c[0] for c in data.columns]

    # Ensure target directory exists
    csv_path = Path(filename)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    # Reset index so "Date" is a column; store clean single-level columns
    data = data.reset_index()
    data.to_csv(csv_path, index=False)
    print(f"Saved {symbol} data to {csv_path.resolve()}")


if __name__ == "__main__":
    # Example: download Apple stock data into ../data/AAPL.csv
    download_stock(
        symbol="AAPL",
        start="2015-01-01",
        end="2024-01-01",
        filename="../data/AAPL.csv",
    )


