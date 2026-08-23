import streamlit as st
import plotly.graph_objects as go
from core.market import fetch_history
from core.footprint import enrich
from core.signal_engine import analyze

st.set_page_config(page_title='AEGIS Intelligence',layout='wide')
st.title('⚡ AEGIS Intelligence'); st.caption('Explainable institutional-style market intelligence')
with st.sidebar:
    symbol=st.text_input('Symbol','BTC-USD'); period=st.selectbox('History',['1mo','3mo','6mo','1y'],index=2); interval=st.selectbox('Interval',['1h','1d']); run=st.button('Analyze',type='primary')
if run or 'data' not in st.session_state:
    ticker,df=fetch_history(symbol,period,interval); st.session_state['data']=(ticker,df)
ticker,df=st.session_state['data']; x=enrich(df); d=analyze(x)
tabs=st.tabs(['📡 Decision','🕯 Candle & Delta','🧪 Backtest','🏢 Company Intel','🕵 Investigator'])
with tabs[0]:
    a,b,c=st.columns(3); a.metric('Decision',d['status']); b.metric('Institutional Score',f"{d['score']}/100"); c.metric('Symbol',ticker)
    if d['entry']:
        for col,label,val in zip(st.columns(5),['Entry','Stop','TP1','TP2','TP3'],[d['entry'],d['stop'],*d['targets']]): col.metric(label,f'{val:,.4f}')
    st.subheader('Why?'); [st.success(i) for i in d['reasons']]
    if d['blockers']: st.subheader('Why not?'); [st.error(i) for i in d['blockers']]
    if d['what_changes']: st.subheader('What would change the decision?'); [st.info(i) for i in d['what_changes']]
    fig=go.Figure(data=[go.Candlestick(x=x.index,open=x.Open,high=x.High,low=x.Low,close=x.Close)]); fig.update_layout(height=600,xaxis_rangeslider_visible=False); st.plotly_chart(fig,use_container_width=True)
with tabs[1]:
    st.warning('Delta/CVD here is a candle-derived proxy. True Delta requires aggressor-side trade data.')
    st.dataframe(x[['Close','Volume','relative_volume','delta_proxy','cvd_proxy','liquidity_sweep_high','liquidity_sweep_low','displacement','trend']].tail(100),use_container_width=True); st.line_chart(x[['cvd_proxy']].tail(300))
with tabs[2]: st.info('Backtest engine is the next module in this repository.')
with tabs[3]: st.info('Company financials, SEC filings, management and ownership connectors are the next module.')
with tabs[4]:
    st.write('Evidence-based investigation: separate confirmed facts, correlations and hypotheses.')
    for q in ['What changed in revenue, margins, cash flow or debt?','Who materially influences the company?','Which public events preceded unusual volume or price?','Which conclusions are facts versus hypotheses?']: st.write('• '+q)
