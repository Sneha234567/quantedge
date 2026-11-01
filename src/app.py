import datetime as dt

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import yfinance as yf
from pathlib import Path
from datetime import datetime
import re

from backtest import backtest_long_only, compute_performance_metrics
from indicators import add_indicators
from strategies import (
    buy_and_hold_strategy,
    macd_strategy,
    rsi_reversion_strategy,
    sma_cross_strategy,
)
from auth_db import (
    init_db,
    create_user,
    verify_user,
    add_search,
    get_searches,
    SearchHistory,
    engine,
    Base,
)


STRATEGY_CHOICES = ["Buy & Hold", "SMA Crossover", "RSI Reversion", "MACD"]


def load_data(symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Download historical price data from Yahoo Finance."""
    try:
        data = yf.download(
            symbol, start=start, end=end, group_by="column", progress=False
        )
    except Exception:
        data = pd.DataFrame()

    if data.empty:
        # Fallback: try local CSV in ../data/<symbol>.csv
        local_csv = Path(__file__).parent.parent / "data" / f"{symbol}.csv"
        if local_csv.exists():
            data = pd.read_csv(local_csv, parse_dates=["Date"], index_col="Date")
        else:
            return pd.DataFrame()

    # Flatten potential multiindex columns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [c[0] for c in data.columns]
    return data


def resample_ohlcv(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """
    Resample OHLCV data to the desired frequency.
    freq: 'D' (daily), 'W' (weekly), 'M' (monthly)
    """
    if freq == "D":
        return df
    # Build aggregation only for columns that exist to avoid KeyError (e.g., missing Adj Close)
    agg = {}
    if "Open" in df.columns:
        agg["Open"] = "first"
    if "High" in df.columns:
        agg["High"] = "max"
    if "Low" in df.columns:
        agg["Low"] = "min"
    if "Close" in df.columns:
        agg["Close"] = "last"
    if "Adj Close" in df.columns:
        agg["Adj Close"] = "last"
    if "Volume" in df.columns:
        agg["Volume"] = "sum"

    return df.resample(freq).agg(agg).dropna()


def run_strategy_pipeline(
    df: pd.DataFrame,
    strategy_name: str,
    initial_capital: float,
    position_fraction: float,
) -> tuple[pd.DataFrame, dict]:
    """Apply indicators, chosen strategy, and backtest."""
    df_ind = add_indicators(df)

    if strategy_name == "Buy & Hold":
        df_sig = buy_and_hold_strategy(df_ind)
    elif strategy_name == "SMA Crossover":
        df_sig = sma_cross_strategy(df_ind)
    elif strategy_name == "RSI Reversion":
        df_sig = rsi_reversion_strategy(df_ind)
    else:
        df_sig = macd_strategy(df_ind)

    df_bt = backtest_long_only(
        df_sig,
        initial_capital=initial_capital,
        position_fraction=position_fraction,
    )
    metrics = compute_performance_metrics(df_bt)
    return df_bt, metrics


def main() -> None:
    # Ensure DB schema has latest columns; attempt an upgrade by recreation if needed.
    try:
        init_db()
    except Exception:
        # Try to drop and recreate tables if schema mismatch (SQLite)
        Base.metadata.drop_all(engine)
        init_db()

    # Background styling
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1f2937 50%, #0f172a 100%);
            color: #e5e7eb;
        }
        .block-container { padding-top: 1rem; }
        /* Hide Streamlit top bar and main menu */
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Top row: left searches button, right title
    # Button to open searches overlay; title on the right
    if "show_searches" not in st.session_state:
        st.session_state["show_searches"] = False

    top_left, top_right = st.columns([1, 4])
    with top_left:
        st.title("QuantEdge Pro")
        if st.session_state.get("auth"):
            if st.button("Searches", use_container_width=True):
                st.session_state["show_searches"] = True
    with top_right:
        pass

    # Full-width searches view when toggled
    if st.session_state.get("auth") and st.session_state.get("show_searches"):
        st.markdown("#### Recent searches")
        history_quick = get_searches(st.session_state["user"], limit=50)
        if history_quick:
            df_hist = pd.DataFrame(history_quick)
            cols = ["timestamp", "symbol", "date_range", "strategy", "action"]
            df_hist = df_hist[[c for c in cols if c in df_hist.columns]]
            st.dataframe(df_hist, use_container_width=True)
        else:
            st.write("No history yet.")
        if st.button("Close searches"):
            st.session_state["show_searches"] = False

    # Auth state
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
        st.session_state["user"] = ""

    if not st.session_state["auth"]:
        # Centered login/register forms (shown only when not authenticated)
        col_left, col_center, col_right = st.columns([1, 2, 1])
        with col_center:
            st.markdown("### Login / Register")
            # Use a selectable control so we can programmatically switch to Login after register
            # initialize auth_mode and handle any requested redirect to Login
            if "auth_mode" not in st.session_state:
                st.session_state["auth_mode"] = "Login"
            if st.session_state.get("redirect_to_login"):
                # set before widget instantiation, then clear flag
                st.session_state["auth_mode"] = "Login"
                del st.session_state["redirect_to_login"]

            auth_mode = st.radio("Authentication mode", ["Login", "Register"], index=0 if st.session_state["auth_mode"] == "Login" else 1, horizontal=True, key="auth_mode")

            if auth_mode == "Login":
                u = st.text_input("Username", key="login_user")
                p = st.text_input("Password", type="password", key="login_pass")
                if st.button("Login"):
                    if verify_user(u, p):
                        st.session_state["auth"] = True
                        st.session_state["user"] = u
                        st.success("Logged in")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

            else:
                ru = st.text_input("New username", key="reg_user")
                rp = st.text_input("New password", type="password", key="reg_pass")
                rc = st.text_input("Confirm password", type="password", key="reg_conf")

                def valid_pw(pw: str) -> str | None:
                    if len(pw) < 6:
                        return "Password must be at least 6 characters."
                    if not re.search(r"[A-Z]", pw):
                        return "Must include an uppercase letter."
                    if not re.search(r"[a-z]", pw):
                        return "Must include a lowercase letter."
                    if not re.search(r"[0-9]", pw):
                        return "Must include a digit."
                    if not re.search(r"[^A-Za-z0-9]", pw):
                        return "Must include a special character."
                    return None

                if st.button("Register"):
                    if rp != rc:
                        st.error("Passwords do not match.")
                    else:
                        err = valid_pw(rp)
                        if err:
                            st.error(err)
                        else:
                            try:
                                create_user(ru, rp)
                                # After successful registration, request redirect to Login
                                st.session_state["redirect_to_login"] = True
                                st.success("User created. Redirecting to login...")
                                # Use getattr to avoid AttributeError on older/newer Streamlit versions
                                rerun_fn = getattr(st, "experimental_rerun", None)
                                if callable(rerun_fn):
                                    rerun_fn()
                                else:
                                    st.info("Please refresh the page or click Login to continue.")
                                    st.stop()
                            except ValueError as e:
                                st.error(str(e))

        st.info("Please log in to use the app.")
        st.stop()
    else:
        st.success(f"Logged in as {st.session_state['user']}")

    username = st.session_state["user"]

    st.sidebar.header("User Inputs")
    symbol = st.sidebar.text_input("Ticker symbol", value="AAPL")

    today = dt.date.today()
    default_start = today.replace(year=today.year - 5)

    start_date = st.sidebar.date_input("Start date", value=default_start)
    end_date = st.sidebar.date_input("End date", value=today)

    initial_capital = st.sidebar.number_input(
        "Initial capital", min_value=1000.0, value=10_000.0, step=1000.0
    )

    freq_choice = st.sidebar.selectbox(
        "Time period (resample)", ["Daily", "Weekly", "Monthly"], index=0
    )
    freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "M"}
    freq = freq_map[freq_choice]

    strategy_name = st.sidebar.selectbox("Strategy", STRATEGY_CHOICES)

    risk_pref = st.sidebar.selectbox(
        "Risk preference (position sizing)",
        ["Low", "Medium", "High"],
        index=1,
    )
    risk_fraction = {"Low": 0.5, "Medium": 0.75, "High": 1.0}[risk_pref]

    run_button = st.sidebar.button("Run Backtest")

    if not run_button:
        # show history
        st.subheader(f"Recent searches for {username}")
        history = get_searches(username, limit=10)
        if history:
            st.table(history)
        else:
            st.info("No previous searches yet.")
        st.info("Set your inputs on the left and click **Run Backtest**.")
        return

    with st.spinner("Downloading data and running backtest..."):
        df_raw = load_data(symbol, start_date, end_date)

        if df_raw.empty:
            st.error("No data returned. Check the symbol and date range.")
            return

        # Resample once and reuse for all strategies
        df_resampled = resample_ohlcv(df_raw, freq)

        # Selected strategy run
        df_bt, metrics = run_strategy_pipeline(
            df_resampled, strategy_name, initial_capital, risk_fraction
        )

        # Strategy comparison on same data/risk
        comparison = {}
        for name in STRATEGY_CHOICES:
            df_cmp, met_cmp = run_strategy_pipeline(
                df_resampled, name, initial_capital, risk_fraction
            )
            comparison[name] = met_cmp

        # Log search
        # Derive last trade action (approx) from selected strategy
        action = "N/A"
        if "position_change" in df_bt.columns:
            trades = df_bt[df_bt["position_change"] != 0]
            if not trades.empty:
                last = trades.iloc[-1]
                action = "Buy" if last["position_change"] > 0 else "Sell"

        add_search(
            username=username,
            symbol=symbol,
            date_range=f"{start_date} to {end_date} ({freq_choice})",
            strategy=strategy_name,
            timestamp=datetime.utcnow().isoformat(),
            action=action,
        )

    st.subheader("Performance Metrics")
    st.json(metrics)

    st.subheader("Strategy Comparison (end value)")
    comp_df = (
        pd.DataFrame(comparison)
        .T[["end_value", "total_return", "sharpe_ratio", "max_drawdown"]]
        .rename(columns={"end_value": "final_value"})
    )
    st.dataframe(comp_df)
    st.bar_chart(comp_df["final_value"])

    # Trade signals table for the selected strategy
    st.subheader("Trade signals (selected strategy)")
    if "position_change" in df_bt.columns:
        trades = df_bt[df_bt["position_change"] != 0].copy()
        trades["Action"] = trades["position_change"].apply(
            lambda x: "Buy" if x > 0 else "Sell"
        )
        trades_view = (
            trades.reset_index()[["Date", "Action", "Close"]]
            .rename(columns={"Close": "Price"})
            .tail(20)
        )
        st.dataframe(trades_view)
    else:
        st.info("No discrete trade signals available for this strategy.")

    st.subheader(f"{symbol} Price and Signals ({strategy_name}) — {freq_choice}")
    fig, (ax_price, ax_pv) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    ax_price.plot(df_bt.index, df_bt["Close"], label="Price")
    if "SMA_20" in df_bt.columns and "SMA_50" in df_bt.columns:
        ax_price.plot(df_bt.index, df_bt["SMA_20"], label="SMA 20")
        ax_price.plot(df_bt.index, df_bt["SMA_50"], label="SMA 50")

    if "position_change" in df_bt.columns:
        buys = df_bt[df_bt["position_change"] == 1]
        sells = df_bt[df_bt["position_change"] == -1]
        ax_price.scatter(buys.index, buys["Close"], marker="^", color="g", label="Buy")
        ax_price.scatter(sells.index, sells["Close"], marker="v", color="r", label="Sell")

    ax_price.legend()
    ax_price.set_ylabel("Price")

    ax_pv.plot(df_bt.index, df_bt["portfolio_value"], label="Portfolio value")
    ax_pv.set_ylabel("Portfolio value")
    ax_pv.legend()

    plt.tight_layout()
    st.pyplot(fig)


if __name__ == "__main__":
    main()






