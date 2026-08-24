"""Market data adapters for AEGIS.

Crypto uses Binance public exchange data. Stocks and forex use Alpha Vantage when
ALPHA_VANTAGE_API_KEY is supplied through Streamlit secrets or an environment
variable, with Yahoo Finance as a clearly labelled fallback.
"""
from __future__ import annotations
import os
import requests
import pandas as pd
import yfinance as yf

BINANCE = "https://api.binance.com/api/v3"
AV = "https://www.alphavantage.co/query"


def _secret(name):
    try:
        import streamlit as st
        return st.secrets.get(name, os.getenv(name, ""))
    except Exception:
        return os.getenv(name, "")


def classify_asset(symbol):
    s = symbol.strip().upper().replace("/", "").replace("-", "")
    crypto_bases = {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "BNB", "AVAX", "LINK", "DOT", "TRX", "SUI"}
    if any(s.startswith(b) and s[len(b):] in {"USD", "USDT", "USDC", "BTC", "ETH"} for b in crypto_bases):
        return "crypto"
    if s.endswith(("USDT", "USDC", "BUSD")) and len(s) >= 6:
        return "crypto"
    if len(s) == 6 and s.isalpha():
        return "forex"
    return "stock"


def normalize_symbol(symbol):
    s = symbol.strip().upper()
    aliases = {"BTC": "BTC-USD", "ETH": "ETH-USD", "GOLD": "GC=F", "S&P500": "^GSPC"}
    if s in aliases:
        return aliases[s]
    compact = s.replace("/", "").replace("-", "")
    if classify_asset(s) == "forex":
        return compact + "=X"
    return s


def _binance_symbol(symbol):
    return symbol.upper().replace("-", "").replace("/", "")


def _binance_interval(interval):
    return {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d"}.get(interval, "1h")


def fetch_binance(symbol, interval="1h", limit=500):
    sym = _binance_symbol(symbol)
    r = requests.get(f"{BINANCE}/klines", params={"symbol": sym, "interval": _binance_interval(interval), "limit": limit}, timeout=15)
    r.raise_for_status()
    rows = r.json()
    df = pd.DataFrame(rows, columns=["open_time", "Open", "High", "Low", "Close", "Volume", "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"])
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df.index = pd.to_datetime(df.pop("open_time"), unit="ms", utc=True)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna(), {"source": "Binance", "freshness": "LIVE / exchange API", "asset_type": "crypto"}


def fetch_binance_quote(symbol):
    sym = _binance_symbol(symbol)
    r = requests.get(f"{BINANCE}/ticker/24hr", params={"symbol": sym}, timeout=10)
    r.raise_for_status()
    q = r.json()
    return {"price": float(q["lastPrice"]), "change_pct": float(q["priceChangePercent"]), "source": "Binance", "freshness": "LIVE / exchange API"}


def _av_params(symbol, interval, asset_type, key):
    interval_map = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "60min", "4h": "60min"}
    if asset_type == "forex":
        s = symbol.upper().replace("/", "").replace("-", "")
        if interval == "1d":
            return {"function": "FX_DAILY", "from_symbol": s[:3], "to_symbol": s[3:], "outputsize": "compact", "apikey": key}
        return {"function": "FX_INTRADAY", "from_symbol": s[:3], "to_symbol": s[3:], "interval": interval_map.get(interval, "60min"), "outputsize": "compact", "apikey": key}
    if interval == "1d":
        return {"function": "TIME_SERIES_DAILY", "symbol": symbol.upper(), "outputsize": "compact", "apikey": key}
    return {"function": "TIME_SERIES_INTRADAY", "symbol": symbol.upper(), "interval": interval_map.get(interval, "60min"), "outputsize": "compact", "apikey": key}


def fetch_alpha_vantage(symbol, interval="1h", asset_type="stock"):
    key = _secret("ALPHA_VANTAGE_API_KEY")
    if not key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is not configured")
    r = requests.get(AV, params=_av_params(symbol, interval, asset_type, key), timeout=25)
    r.raise_for_status()
    data = r.json()
    series = next((v for k, v in data.items() if "Time Series" in k), None)
    if not series:
        raise RuntimeError(data.get("Note") or data.get("Information") or data.get("Error Message") or "No Alpha Vantage series returned")
    df = pd.DataFrame(series).T.rename(columns=lambda c: c.split(". ")[-1].title())
    for c in ["Open", "High", "Low", "Close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce") if "Volume" in df else 0
    df.index = pd.to_datetime(df.index, utc=True)
    freshness = "Provider entitlement dependent" if interval != "1d" else "Latest provider daily series"
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna().sort_index(), {"source": "Alpha Vantage", "freshness": freshness, "asset_type": asset_type}


def fetch_yfinance(symbol, period="6mo", interval="1h"):
    ticker = normalize_symbol(symbol)
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
    if df.empty:
        raise ValueError(f"No data returned for {ticker}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df.columns = [str(c).title() for c in df.columns]
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c not in df:
            df[c] = 0
    return ticker, df[["Open", "High", "Low", "Close", "Volume"]].dropna(), {"source": "Yahoo Finance", "freshness": "Provider dependent / not guaranteed real-time", "asset_type": classify_asset(symbol)}


def fetch_history(symbol, period="6mo", interval="1h", provider="auto"):
    asset = classify_asset(symbol)
    if provider == "auto" and asset == "crypto":
        try:
            df, meta = fetch_binance(symbol, interval)
            return _binance_symbol(symbol), df, meta
        except Exception:
            pass
    if provider in ("auto", "alpha") and asset in ("stock", "forex") and _secret("ALPHA_VANTAGE_API_KEY"):
        try:
            df, meta = fetch_alpha_vantage(symbol, interval, asset)
            return normalize_symbol(symbol), df, meta
        except Exception:
            pass
    ticker, df, meta = fetch_yfinance(symbol, period, interval)
    return ticker, df, meta
