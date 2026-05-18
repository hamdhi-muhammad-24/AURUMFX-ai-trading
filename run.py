"""
AURUMFx AI Trading System — Launcher
Usage:
  python run.py                   # Run full MVP cycle (EURUSD M15)
  python run.py --dashboard       # Start Streamlit dashboard
  python run.py --api             # Start FastAPI backend
  python run.py --backtest        # Run backtest on EURUSD M15
  python run.py --symbol XAUUSD   # Override symbol
  python run.py --generate-data   # Generate sample CSV data
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_mvp_cycle(symbol: str, timeframe: str, retrain: bool = False):
    """Run a single AI analysis cycle and print the result."""
    print(f"\nRunning AURUMFx analysis: {symbol} {timeframe}")
    print("=" * 60)

    from database.db import init_db
    from core.calendar_news import create_sample_calendar
    from core.agent import run_cycle

    init_db()
    create_sample_calendar()

    output = run_cycle(symbol=symbol, timeframe=timeframe, force_retrain=retrain)

    print(f"\nSIGNAL   : {output.signal}")
    print(f"CONFIDENCE: {output.confidence:.0%}")
    print(f"PRICE    : {output.price:.5f}")
    print(f"ML MODEL : {output.ml_model_used} ({output.ml_signal} @ {output.ml_confidence:.0%})")
    print(f"EMA TREND: {output.ema_trend}")
    print(f"RSI      : {output.rsi:.1f}")
    print(f"ATR pips : {output.atr_pips:.1f}")
    print(f"STRUCTURE: {output.structure_label}")
    print(f"BOS      : {output.bos}")

    if output.signal in ("BUY", "SELL"):
        print(f"\nTRADE SETUP")
        print(f"  Entry  : {output.entry_price:.5f}")
        print(f"  SL     : {output.sl_price:.5f} ({output.sl_pips:.1f} pips)")
        print(f"  TP     : {output.tp_price:.5f} ({output.tp_pips:.1f} pips)")
        print(f"  Lot    : {output.lot_size}")
        print(f"  Risk   : ${output.risk_amount:.2f}")
        print(f"  RR     : 1:{output.risk_reward:.2f}")

    if output.blocks:
        print(f"\nBLOCKED BY: {', '.join(output.blocks)}")
    if output.supports:
        print(f"SUPPORTED BY: {', '.join(output.supports)}")

    if output.paper_trade_opened:
        print(f"\nPaper trade #{output.paper_trade_id} opened")

    if output.error:
        print(f"\nERROR: {output.error}")

    print("\n" + "-" * 60)
    print("EXPLANATION:")
    # Strip non-ASCII for Windows console compatibility
    explanation = output.explanation.encode("ascii", errors="replace").decode("ascii")
    print(explanation)
    print("=" * 60)
    return output


def run_backtest_cli(symbol: str, timeframe: str):
    """Run backtest and print summary."""
    from database.db import init_db
    from core.data_loader import get_candles
    from core.backtester import run_backtest, save_backtest_result
    from config import settings

    init_db()
    print(f"\nRunning backtest: {symbol} {timeframe}")
    df = get_candles(symbol, timeframe, n_bars=settings.TRAIN_LOOKBACK)
    if df.empty:
        print("ERROR: No data available for backtest")
        return

    result = run_backtest(df, symbol, timeframe)
    save_backtest_result(result)

    print(f"\nBacktest Results: {symbol} {timeframe}")
    print(f"  Period       : {result.start_date} -> {result.end_date}")
    print(f"  Total trades : {result.total_trades}")
    print(f"  Win rate     : {result.win_rate:.1f}%")
    print(f"  Profit factor: {result.profit_factor:.3f}")
    print(f"  Max drawdown : {result.max_drawdown_pct:.1f}%")
    print(f"  Total pips   : {result.total_pips:+.1f}")
    print(f"  Final balance: ${result.final_balance:,.2f}")
    print(f"  Sharpe ratio : {result.sharpe_ratio:.3f}")
    print(f"  Blocked      : {result.blocked_count}")
    print(f"  No trade     : {result.no_trade_count}")


def start_dashboard():
    print("Starting Streamlit dashboard at http://localhost:8501")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        os.path.join(os.path.dirname(__file__), "dashboard", "app.py"),
        "--server.port", "8501",
        "--server.address", "0.0.0.0",
        "--browser.gatherUsageStats", "false",
    ])


def start_api():
    from config import settings
    print(f"Starting FastAPI at http://{settings.API_HOST}:{settings.API_PORT}")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "api.main:app",
        "--host", settings.API_HOST,
        "--port", str(settings.API_PORT),
        "--reload" if settings.API_RELOAD else "",
    ])


def generate_data():
    print("Generating sample candle data...")
    from scripts.generate_sample_data import main as gen_main
    gen_main()


def main():
    parser = argparse.ArgumentParser(description="AURUMFx AI Trading System")
    parser.add_argument("--dashboard", action="store_true", help="Start Streamlit dashboard")
    parser.add_argument("--api", action="store_true", help="Start FastAPI backend")
    parser.add_argument("--backtest", action="store_true", help="Run backtest")
    parser.add_argument("--generate-data", action="store_true", help="Generate sample CSV data")
    parser.add_argument("--symbol", default="EURUSD", help="Symbol (default: EURUSD)")
    parser.add_argument("--timeframe", default="M15", help="Timeframe (default: M15)")
    parser.add_argument("--retrain", action="store_true", help="Force model retrain")
    args = parser.parse_args()

    if args.generate_data:
        generate_data()
    elif args.dashboard:
        start_dashboard()
    elif args.api:
        start_api()
    elif args.backtest:
        run_backtest_cli(args.symbol, args.timeframe)
    else:
        # Default: run MVP cycle
        run_mvp_cycle(args.symbol, args.timeframe, args.retrain)


if __name__ == "__main__":
    main()
