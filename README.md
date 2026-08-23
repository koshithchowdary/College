# AEGIS Intelligence

Explainable institutional-style market intelligence platform.

## Current MVP
- BUY / SELL / WATCH / NO TRADE
- Explicit reasons for every decision and rejection
- Candle footprint analysis
- Liquidity sweeps and displacement
- Relative volume
- Delta/CVD proxy mode when true aggressor-side data is unavailable
- Entry, stop loss and TP targets
- Historical backtesting
- Company intelligence foundation
- Investigator Mode for evidence-based public-information research

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

> Research and decision-support software only. Signals are not guarantees of profitability.

## Data integrity
OHLCV candles alone cannot identify exact buyer-initiated versus seller-initiated volume. Delta/CVD is therefore explicitly labeled as an estimate unless a true order-flow provider is connected.
