import yfinance as yf
import pandas as pd

def normalize_symbol(symbol: str) -> str:
    aliases = {"BTC":"BTC-USD","ETH":"ETH-USD","GOLD":"GC=F","S&P500":"^GSPC"}
    return aliases.get(symbol.strip().upper(), symbol.strip().upper())

def fetch_history(symbol, period="6mo", interval="1h"):
    ticker = normalize_symbol(symbol)
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
    if df.empty: raise ValueError(f"No data returned for {ticker}")
    if isinstance(df.columns, pd.MultiIndex): df.columns=[c[0] for c in df.columns]
    df.columns=[str(c).title() for c in df.columns]
    for c in ["Open","High","Low","Close","Volume"]:
        if c not in df: df[c]=0
    return ticker, df.dropna()
