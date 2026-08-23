# AEGIS Intelligence

Explainable institutional-style market intelligence platform.

## Current MVP
- BUY / SELL / WATCH / NO TRADE
- Explicit reasons for every decision and rejection
- Candle footprint analysis
- Liquidity sweeps and displacement
- Relative volume
- Candle-derived Delta/CVD proxy for markets without aggressor-side data
- **True crypto Delta/CVD from Binance Spot aggregate trades**
- Taker buy/sell classification using the exchange-supplied `isBuyerMaker` / `m` field
- Per-minute Delta and Cumulative Volume Delta
- Prepared public WebSocket endpoint for real-time aggregate-trade streaming
- Entry, stop loss and TP targets
- Historical backtesting architecture
- Company intelligence foundation
- Investigator Mode for evidence-based public-information research

## True Delta convention
For Binance aggregate trades, `m=true` means the buyer was the market maker, so the taker initiated a sell and the trade contributes negative Delta. `m=false` contributes positive Delta as a taker-initiated buy. Aggregate trades may represent multiple fills belonging to one taker order at the same price/time.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

> Research and decision-support software only. Signals are not guarantees of profitability.

## Data integrity
OHLCV candles alone cannot identify exact buyer-initiated versus seller-initiated volume. AEGIS therefore keeps candle-derived Delta clearly separated from exchange-classified order-flow Delta. True order-flow availability is exchange and market dependent.
