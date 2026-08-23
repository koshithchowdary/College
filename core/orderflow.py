"""True crypto order-flow adapter for Binance Spot public market data.

Delta convention:
- buyer is maker (m=True) => seller was taker => negative delta
- buyer is not maker (m=False) => buyer was taker => positive delta

The adapter never calls this data a proxy: values are computed from the
exchange-supplied maker/taker flag on aggregate trades. Aggregate trades may
combine multiple fills from one taker order at the same price/time.
"""
from __future__ import annotations
import time
import requests
import pandas as pd

BASE_URL = "https://data-api.binance.vision"


def normalize_crypto_symbol(symbol: str) -> str:
    s = symbol.upper().replace("-", "").replace("/", "").replace("_", "")
    for suffix in ("USDT", "USDC", "BUSD", "USD", "BTC", "ETH"):
        if s.endswith(suffix):
            return s
    raise ValueError("Use an exchange symbol such as BTCUSDT, ETHUSDT or BTC/USDT")


def fetch_agg_trades(symbol: str, limit: int = 1000) -> pd.DataFrame:
    pair = normalize_crypto_symbol(symbol)
    r = requests.get(
        f"{BASE_URL}/api/v3/aggTrades",
        params={"symbol": pair, "limit": max(1, min(int(limit), 1000))},
        timeout=10,
    )
    r.raise_for_status()
    raw = r.json()
    if not raw:
        return pd.DataFrame(columns=["time", "price", "qty", "quote_qty", "side", "delta"])
    df = pd.DataFrame(raw)
    df["time"] = pd.to_datetime(df["T"], unit="ms", utc=True)
    df["price"] = pd.to_numeric(df["p"], errors="coerce")
    df["qty"] = pd.to_numeric(df["q"], errors="coerce")
    df["quote_qty"] = df["price"] * df["qty"]
    # m=true means buyer was maker, therefore the taker initiated a sell.
    df["side"] = df["m"].map({True: "SELL", False: "BUY"})
    df["delta"] = df["quote_qty"].where(df["side"].eq("BUY"), -df["quote_qty"])
    return df[["time", "price", "qty", "quote_qty", "side", "delta"]]


def orderflow_summary(symbol: str, limit: int = 1000, bucket: str = "1min"):
    trades = fetch_agg_trades(symbol, limit)
    if trades.empty:
        return trades, {"delta": 0.0, "cvd": 0.0, "buy_quote": 0.0, "sell_quote": 0.0, "imbalance": 0.0}
    buy_quote = float(trades.loc[trades.side == "BUY", "quote_qty"].sum())
    sell_quote = float(trades.loc[trades.side == "SELL", "quote_qty"].sum())
    delta = buy_quote - sell_quote
    total = buy_quote + sell_quote
    imbalance = delta / total if total else 0.0
    trades["cvd"] = trades["delta"].cumsum()
    bars = (trades.set_index("time")
            .resample(bucket)
            .agg(price=("price", "last"), buy_quote=("quote_qty", lambda s: s[trades.loc[s.index, "side"].eq("BUY")].sum()),
                 sell_quote=("quote_qty", lambda s: s[trades.loc[s.index, "side"].eq("SELL")].sum()), delta=("delta", "sum")))
    bars["cvd"] = bars["delta"].fillna(0).cumsum()
    return bars.dropna(how="all"), {"delta": float(delta), "cvd": float(trades["cvd"].iloc[-1]), "buy_quote": buy_quote, "sell_quote": sell_quote, "imbalance": float(imbalance), "trades": int(len(trades))}


def websocket_url(symbol: str) -> str:
    pair = normalize_crypto_symbol(symbol).lower()
    return f"wss://data-stream.binance.vision/ws/{pair}@aggTrade"


def parse_stream_trade(message: dict) -> dict:
    price = float(message["p"]); qty = float(message["q"])
    quote_qty = price * qty
    side = "SELL" if message.get("m") else "BUY"
    return {"time": pd.to_datetime(message["T"], unit="ms", utc=True), "price": price, "qty": qty,
            "quote_qty": quote_qty, "side": side, "delta": -quote_qty if side == "SELL" else quote_qty}
