import streamlit as st
import plotly.graph_objects as go
from core.market import fetch_history
from core.footprint import enrich
from core.signal_engine import analyze
from core.orderflow import orderflow_summary, websocket_url

st.set_page_config(page_title='AEGIS Intelligence',layout='wide')
st.title('⚡ AEGIS Intelligence'); st.caption('Explainable institutional-style market intelligence')
with st.sidebar:
    symbol=st.text_input('Symbol','BTC-USD'); period=st.selectbox('History',['1mo','3mo','6mo','1y'],index=2); interval=st.selectbox('Interval',['1h','1d']); run=st.button('Analyze',type='primary')
if run or 'data' not in st.session_state:
    ticker,df=fetch_history(symbol,period,interval); st.session_state['data']=(ticker,df)
ticker,df=st.session_state['data']; x=enrich(df); d=analyze(x)
tabs=st.tabs(['📡 Decision','🕯 Candle & Delta','⚡ True Order Flow','🧪 Backtest','🏢 Company Intel','🕵 Investigator'])
with tabs[0]:
    a,b,c=st.columns(3); a.metric('Decision',d['status']); b.metric('Institutional Score',f"{d['score']}/100"); c.metric('Symbol',ticker)
    if d['entry']:
        for col,label,val in zip(st.columns(5),['Entry','Stop','TP1','TP2','TP3'],[d['entry'],d['stop'],*d['targets']]): col.metric(label,f'{val:,.4f}')
    st.subheader('Why?'); [st.success(i) for i in d['reasons']]
    if d['blockers']: st.subheader('Why not?'); [st.error(i) for i in d['blockers']]
    if d['what_changes']: st.subheader('What would change the decision?'); [st.info(i) for i in d['what_changes']]
    fig=go.Figure(data=[go.Candlestick(x=x.index,open=x.Open,high=x.High,low=x.Low,close=x.Close)]); fig.update_layout(height=600,xaxis_rangeslider_visible=False); st.plotly_chart(fig,use_container_width=True)
with tabs[1]:
    st.warning('Delta/CVD here is a candle-derived proxy. Use the True Order Flow tab for exchange trade classification.')
    st.dataframe(x[['Close','Volume','relative_volume','delta_proxy','cvd_proxy','liquidity_sweep_high','liquidity_sweep_low','displacement','trend']].tail(100),use_container_width=True); st.line_chart(x[['cvd_proxy']].tail(300))
with tabs[2]:
    st.subheader('True Crypto Order Flow — Binance Spot')
    st.caption('Uses exchange aggregate-trade data and the maker/taker classification. m=true means the buyer was maker, so the taker was selling; m=false is classified as taker buying.')
    pair=st.text_input('Exchange symbol', 'BTCUSDT', key='orderflow_pair')
    limit=st.slider('Recent aggregate trades',100,1000,1000,100)
    if st.button('Refresh true order flow', type='primary') or 'of_result' not in st.session_state:
        try:
            bars,summary=orderflow_summary(pair,limit)
            st.session_state['of_result']=(pair,bars,summary)
        except Exception as e: st.error(f'Order-flow connector error: {e}')
    if 'of_result' in st.session_state:
        pair,bars,summary=st.session_state['of_result']
        a,b,c,d1=st.columns(4)
        a.metric('Net Delta',f"{summary['delta']:,.0f}")
        b.metric('CVD',f"{summary['cvd']:,.0f}")
        c.metric('Imbalance',f"{summary['imbalance']*100:.1f}%")
        d1.metric('Aggregate Trades',summary['trades'])
        st.caption(f'Live stream endpoint prepared: {websocket_url(pair)}')
        if not bars.empty:
            st.subheader('Delta by minute'); st.bar_chart(bars[['delta']])
            st.subheader('Cumulative Volume Delta'); st.line_chart(bars[['cvd']])
            st.dataframe(bars.tail(100),use_container_width=True)
            if summary['imbalance'] > 0.15: st.success('Buyer-initiated flow dominates this sampled window. This is order-flow evidence, not a standalone BUY signal.')
            elif summary['imbalance'] < -0.15: st.error('Seller-initiated flow dominates this sampled window. This is order-flow evidence, not a standalone SELL signal.')
            else: st.info('Order flow is relatively balanced in this sampled window.')
with tabs[3]: st.info('Backtest engine is the next module in this repository.')
with tabs[4]: st.info('Company financials, SEC filings, management and ownership connectors are the next module.')
with tabs[5]:
    st.write('Evidence-based investigation: separate confirmed facts, correlations and hypotheses.')
    for q in ['What changed in revenue, margins, cash flow or debt?','Who materially influences the company?','Which public events preceded unusual volume or price?','Which conclusions are facts versus hypotheses?']: st.write('• '+q)
