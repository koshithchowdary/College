import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from core.market import fetch_history, classify_asset, fetch_binance_quote
from core.footprint import enrich
from core.signal_engine import analyze
from core.orderflow import orderflow_summary
from core.backtest import run_backtest, get_trade_analysis, get_side_analysis, get_equity_curve, calculate_kelly_criterion
from core.company import get_company_profile, get_crypto_fundamentals
from core.investigator import create_investigation_report, analyze_revenue_changes

st.set_page_config(page_title="AEGIS Intelligence", layout="wide")
st.title("⚡ AEGIS Intelligence")
st.caption("Explainable institutional-style market intelligence — every signal and rejection has a reason.")

with st.sidebar:
    st.header("Market")
    symbol=st.text_input("Symbol", "BTCUSDT", help="Crypto: BTCUSDT. Stocks: AAPL. Forex: EURUSD or EUR/USD.")
    period=st.selectbox("History",["1mo","3mo","6mo","1y","2y"],index=2)
    interval=st.selectbox("Interval",["1m","5m","15m","30m","1h","4h","1d"],index=4)
    if st.button("🔄 Refresh analysis",type="primary"): st.session_state.pop("market",None)

if "market" not in st.session_state:
    try: st.session_state["market"]=fetch_history(symbol,period,interval)
    except Exception as e: st.error(f"Market data error: {e}"); st.stop()

ticker,df,meta=st.session_state["market"]
x=enrich(df); d=analyze(x); asset=meta.get("asset_type",classify_asset(symbol))

st.info(f"**Data source:** {meta['source']}  |  **Freshness:** {meta['freshness']}  |  **Asset type:** {asset}")
if asset=="crypto":
    try:
        q=fetch_binance_quote(symbol); st.caption(f"Live exchange quote: {q['price']:,.8f} | 24h: {q['change_pct']:.2f}%")
    except Exception: pass

tabs=st.tabs(["📡 Decision","🕯 Candle & Delta","⚡ True Order Flow","🧪 Backtest","🏢 Company Intel","🕵 Investigator"])

with tabs[0]:
    a,b,c=st.columns(3); a.metric("Decision",d["status"]); b.metric("Institutional Score",f"{d['score']}/100"); c.metric("Symbol",ticker)
    if d.get("entry"):
        cols=st.columns(5)
        vals=[d["entry"],d["stop"],*d["targets"]]
        for col,label,val in zip(cols,["Entry","Stop","TP1","TP2","TP3"],vals): col.metric(label,f"{val:,.6f}")
    st.subheader("Why?")
    for r in d.get("reasons",[]): st.success(r)
    if d.get("blockers"):
        st.subheader("Why not?")
        for r in d["blockers"]: st.error(r)
    if d.get("what_changes"):
        st.subheader("What would change the decision?")
        for r in d["what_changes"]: st.info(r)
    fig=go.Figure(data=[go.Candlestick(x=x.index,open=x.Open,high=x.High,low=x.Low,close=x.Close)])
    fig.update_layout(height=600,xaxis_rangeslider_visible=False,title=f"{ticker} price action")
    st.plotly_chart(fig,use_container_width=True)

with tabs[1]:
    st.warning("Delta/CVD below is a candle-derived proxy. It is not true aggressor-side Delta.")
    st.dataframe(x[["Close","Volume","relative_volume","delta_proxy","cvd_proxy","liquidity_sweep_high","liquidity_sweep_low","displacement","trend"]].tail(100),use_container_width=True)
    st.line_chart(x[["cvd_proxy"]].tail(300))

with tabs[2]:
    if asset!="crypto": st.info("True exchange Delta is currently enabled for Binance Spot crypto symbols. Other markets keep the proxy until a suitable order-flow feed is connected.")
    else:
        pair=st.text_input("Binance symbol",ticker,key="pair"); limit=st.slider("Aggregate trades",100,1000,500,100)
        if st.button("Refresh true order flow",type="primary"):
            try: st.session_state["of"]=orderflow_summary(pair,limit)
            except Exception as e: st.error(str(e))
        if "of" in st.session_state:
            bars,summary=st.session_state["of"]; a,b,c,d1=st.columns(4)
            a.metric("Net Delta",f"{summary['delta']:,.2f}"); b.metric("CVD",f"{summary['cvd']:,.2f}"); c.metric("Imbalance",f"{summary['imbalance']*100:.1f}%"); d1.metric("Trades",summary["trades"])
            if not bars.empty: st.bar_chart(bars[["delta"]]); st.line_chart(bars[["cvd"]])

with tabs[3]:
    warmup=st.slider("Warmup candles",20,120,60); holding=st.slider("Max holding candles",5,50,25)
    if st.button("Run Backtest",type="primary"):
        trades,metrics=run_backtest(df,warmup=warmup,holding=holding); st.session_state["bt"]=(trades,metrics)
    if "bt" in st.session_state:
        trades,metrics=st.session_state["bt"]
        if trades.empty: st.warning("No trades generated on this sample.")
        else:
            cols=st.columns(5)
            for col,k,label in zip(cols,["trades","win_rate","profit_factor","net_pnl","max_drawdown"],["Trades","Win Rate %","Profit Factor","Net P&L %","Max DD %"]): col.metric(label,str(metrics[k]))
            st.metric("Conservative Kelly %",f"{calculate_kelly_criterion(trades):.2f}%")
            eq=get_equity_curve(trades); st.line_chart(eq)
            st.subheader("By exit reason"); st.json(get_trade_analysis(trades))
            st.subheader("By side"); st.json(get_side_analysis(trades))
            st.dataframe(trades,use_container_width=True)

with tabs[4]:
    if asset=="crypto":
        if st.button("Load crypto intelligence",type="primary"):
            try: st.session_state["ci"]=("crypto",get_crypto_fundamentals(symbol))
            except Exception as e: st.error(str(e))
    elif asset=="stock":
        if st.button("Load company intelligence",type="primary"):
            try: st.session_state["ci"]=("stock",get_company_profile(ticker))
            except Exception as e: st.error(str(e))
    else: st.info("Company intelligence applies to listed companies. Forex intelligence is handled through macro/event modules in a future connector.")
    if "ci" in st.session_state:
        kind,data=st.session_state["ci"]
        if kind=="crypto": st.json(data)
        else:
            st.subheader(data["basic_info"].get("company_name","Company")); st.json(data["basic_info"])
            st.metric("Financial Health Score",f"{data['financial_health']['health_score']}/100")
            for f in data["financial_health"]["factors"]: st.write("• "+f)
            if not data["income_statement"].empty: st.dataframe(data["income_statement"],use_container_width=True)
            if not data["cash_flow"].empty: st.dataframe(data["cash_flow"],use_container_width=True)
            if not data["sec_filings"].empty: st.dataframe(data["sec_filings"],use_container_width=True)

with tabs[5]:
    st.subheader("Evidence-based Investigator")
    st.caption("Facts, correlations and hypotheses are deliberately separated. Timing is not treated as proof of causation.")
    if st.button("Run investigation",type="primary"):
        try:
            profile=get_company_profile(ticker) if asset=="stock" else {"sec_filings":pd.DataFrame()}
            st.session_state["inv"]=create_investigation_report(ticker,profile,df)
        except Exception as e: st.error(str(e))
    if "inv" in st.session_state:
        report=st.session_state["inv"]
        st.write("### Confirmed facts"); [st.success(v) for v in report["confirmed_facts"]]
        st.write("### Correlations"); st.dataframe(pd.DataFrame(report["correlations"]),use_container_width=True)
        st.write("### Price/volume anomalies"); st.dataframe(pd.DataFrame(report["anomalies"]),use_container_width=True)
        st.write("### Hypotheses / leads"); [st.info(v) for v in report["hypotheses"]]
