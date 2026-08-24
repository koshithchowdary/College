import streamlit as st
import plotly.graph_objects as go
from core.market import fetch_history
from core.footprint import enrich
from core.signal_engine import analyze
from core.orderflow import orderflow_summary, websocket_url
from core.backtest import run_backtest, get_trade_analysis, get_side_analysis, get_equity_curve, calculate_kelly_criterion
from core.company import get_company_profile, set_alpha_vantage_key, get_crypto_fundamentals
from core.investigator import Investigation, analyze_revenue_changes, find_volume_price_anomalies, correlate_events_to_price, create_investigation_report

st.set_page_config(page_title='AEGIS Intelligence', layout='wide')
st.title('⚡ AEGIS Intelligence')
st.caption('Explainable institutional-style market intelligence')

# Sidebar configuration
with st.sidebar:
    st.header('⚙️ Configuration')
    
    # Alpha Vantage API Key setup
    with st.expander('🔑 API Setup'):
        av_key = st.text_input('Alpha Vantage API Key', type='password', help='Get free at https://www.alphavantage.co/')
        if av_key:
            set_alpha_vantage_key(av_key)
            st.success('Alpha Vantage API configured!')
    
    symbol = st.text_input('Symbol', 'BTC-USD')
    period = st.selectbox('History', ['1mo', '3mo', '6mo', '1y'], index=2)
    interval = st.selectbox('Interval', ['1h', '1d'])
    run = st.button('Analyze', type='primary')

# Load market data
if run or 'data' not in st.session_state:
    ticker, df = fetch_history(symbol, period, interval)
    st.session_state['data'] = (ticker, df)

ticker, df = st.session_state['data']
x = enrich(df)
d = analyze(x)

# Create tabs
tabs = st.tabs(['📡 Decision', '🕯 Candle & Delta', '⚡ True Order Flow', '🧪 Backtest', '🏢 Company Intel', '🕵 Investigator'])

# Tab 0: Decision
with tabs[0]:
    st.subheader('Trading Decision')
    a, b, c = st.columns(3)
    a.metric('Decision', d['status'])
    b.metric('Institutional Score', f"{d['score']}/100")
    c.metric('Symbol', ticker)
    
    if d['entry']:
        st.subheader('Price Targets')
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric('Entry', f'{d["entry"]:,.4f}')
        col2.metric('Stop Loss', f'{d["stop"]:,.4f}')
        col3.metric('TP1', f'{d["targets"][0]:,.4f}')
        col4.metric('TP2', f'{d["targets"][1]:,.4f}')
        col5.metric('TP3', f'{d["targets"][2]:,.4f}')
    
    if d['reasons']:
        st.subheader('✅ Why?')
        for reason in d['reasons']:
            st.success(reason)
    
    if d['blockers']:
        st.subheader('❌ Why not?')
        for blocker in d['blockers']:
            st.error(blocker)
    
    if d['what_changes']:
        st.subheader('⚠️ What would change the decision?')
        for change in d['what_changes']:
            st.info(change)
    
    # Candlestick chart
    fig = go.Figure(data=[go.Candlestick(
        x=x.index,
        open=x.Open,
        high=x.High,
        low=x.Low,
        close=x.Close,
        name='Price'
    )])
    fig.update_layout(height=600, xaxis_rangeslider_visible=False, title=f'{ticker} Price Action')
    st.plotly_chart(fig, use_container_width=True)


# Tab 1: Candle & Delta
with tabs[1]:
    st.subheader('📊 Candle Analysis & Delta')
    st.warning('Delta/CVD here is a candle-derived proxy. Use the True Order Flow tab for exchange trade classification.')
    
    # Display metrics
    df_display = x[['Close', 'Volume', 'relative_volume', 'delta_proxy', 'cvd_proxy', 'liquidity_sweep_high', 'liquidity_sweep_low', 'displacement', 'trend']].tail(100).copy()
    st.dataframe(df_display, use_container_width=True)
    
    # Delta chart
    fig_delta = go.Figure()
    fig_delta.add_trace(go.Bar(x=x.index, y=x['delta_proxy'], name='Delta', marker_color='rgba(0,100,200,0.7)'))
    fig_delta.update_layout(height=400, title='Delta Proxy by Candle', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_delta, use_container_width=True)
    
    # CVD chart
    fig_cvd = go.Figure()
    fig_cvd.add_trace(go.Scatter(x=x.index, y=x['cvd_proxy'], mode='lines', name='CVD', line=dict(color='darkblue', width=2)))
    fig_cvd.update_layout(height=400, title='Cumulative Volume Delta (CVD)', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_cvd, use_container_width=True)


# Tab 2: True Order Flow
with tabs[2]:
    st.subheader('⚡ True Crypto Order Flow — Binance Spot')
    st.caption('Uses exchange aggregate-trade data and maker/taker classification. m=true means buyer was maker (seller taker = negative delta). m=false = buyer taker (positive delta).')
    
    col1, col2 = st.columns(2)
    with col1:
        pair = st.text_input('Exchange symbol', 'BTCUSDT', key='orderflow_pair')
    with col2:
        limit = st.slider('Recent aggregate trades', 100, 1000, 1000, 100)
    
    if st.button('Refresh true order flow', type='primary') or 'of_result' not in st.session_state:
        try:
            with st.spinner('Fetching order flow data...'):
                bars, summary = orderflow_summary(pair, limit)
                st.session_state['of_result'] = (pair, bars, summary)
        except Exception as e:
            st.error(f'Order-flow connector error: {e}')
    
    if 'of_result' in st.session_state:
        pair, bars, summary = st.session_state['of_result']
        
        # Metrics
        a, b, c, d1 = st.columns(4)
        a.metric('Net Delta', f"{summary['delta']:,.0f}")
        b.metric('CVD', f"{summary['cvd']:,.0f}")
        c.metric('Imbalance', f"{summary['imbalance']*100:.1f}%")
        d1.metric('Aggregate Trades', summary['trades'])
        
        st.caption(f'Live stream endpoint: `{websocket_url(pair)}`')
        
        if not bars.empty:
            st.subheader('Delta by Minute')
            st.bar_chart(bars[['delta']])
            
            st.subheader('Cumulative Volume Delta')
            st.line_chart(bars[['cvd']])
            
            st.dataframe(bars.tail(100), use_container_width=True)
            
            if summary['imbalance'] > 0.15:
                st.success('✅ Buyer-initiated flow dominates. This is order-flow evidence, not a standalone BUY signal.')
            elif summary['imbalance'] < -0.15:
                st.error('❌ Seller-initiated flow dominates. This is order-flow evidence, not a standalone SELL signal.')
            else:
                st.info('⚠️ Order flow is relatively balanced in this sampled window.')


# Tab 3: Backtest (FUNCTIONAL)
with tabs[3]:
    st.subheader('🧪 Backtest Engine')
    st.info('Historical performance analysis of trading signals on this asset.')
    
    col1, col2, col3 = st.columns(3)
    with col1:
        warmup = st.slider('Warmup candles', 20, 120, 60)
    with col2:
        holding = st.slider('Max holding candles', 5, 50, 25)
    with col3:
        if st.button('Run Backtest', type='primary'):
            st.session_state['backtest_run'] = True
    
    if st.session_state.get('backtest_run', False):
        with st.spinner('Running backtest...'):
            trades, metrics = run_backtest(df, warmup=warmup, holding=holding)
        
        if len(trades) > 0:
            # Performance metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric('Total Trades', metrics['trades'])
            col2.metric('Win Rate', f"{metrics['win_rate']}%")
            col3.metric('Profit Factor', f"{metrics['profit_factor']:.2f}x")
            col4.metric('Net P&L', f"{metrics['net_pnl']:.2f}%")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric('Max Drawdown', f"{metrics['max_drawdown']:.2f}%")
            col2.metric('Avg Win', f"{metrics['avg_win']:.2f}%")
            col3.metric('Avg Loss', f"{metrics['avg_loss']:.2f}%")
            col4.metric('Kelly %', f"{calculate_kelly_criterion(trades):.2f}%")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric('Best Trade', f"{metrics['best_trade']:.2f}%")
            with col2:
                st.metric('Worst Trade', f"{metrics['worst_trade']:.2f}%")
            
            # Equity curve
            st.subheader('Equity Curve')
            equity = get_equity_curve(trades)
            if not equity.empty:
                fig_equity = go.Figure()
                fig_equity.add_trace(go.Scatter(x=equity.index, y=equity['cumulative_return'], mode='lines', name='Equity', line=dict(color='green', width=2)))
                fig_equity.update_layout(height=400, title='Cumulative Equity Growth', yaxis_title='Equity Multiplier')
                st.plotly_chart(fig_equity, use_container_width=True)
            
            # Trade analysis
            st.subheader('Trade Analysis')
            col1, col2 = st.columns(2)
            
            with col1:
                st.write('**By Exit Reason**')
                analysis_by_result = get_trade_analysis(trades)
                for result, stats in analysis_by_result.items():
                    st.write(f"**{result}**: {stats['count']} trades | Win Rate: {stats['win_rate']}% | P&L: {stats['total_pnl']:.2f}%")
            
            with col2:
                st.write('**By Side**')
                analysis_by_side = get_side_analysis(trades)
                for side, stats in analysis_by_side.items():
                    st.write(f"**{side}**: {stats['count']} trades | Win Rate: {stats['win_rate']}% | P&L: {stats['total_pnl']:.2f}%")
            
            # Trade log
            st.subheader('Trade Log')
            st.dataframe(trades[['time', 'side', 'entry', 'exit', 'result', 'pnl_pct', 'score']], use_container_width=True)
        else:
            st.warning('No trades generated. Try adjusting parameters.')


# Tab 4: Company Intel (FUNCTIONAL)
with tabs[4]:
    st.subheader('🏢 Company Intelligence')
    
    # Determine if crypto or stock
    is_crypto = any(ticker.lower().endswith(suffix) for suffix in ['usdt', 'usd', 'btc', 'eth'])
    
    if st.button('Load Company Data', type='primary'):
        with st.spinner('Fetching company intelligence...'):
            if is_crypto:
                crypto_id = ticker.split('-')[0].lower()
                profile = get_company_profile(crypto_id, is_crypto=True)
                
                if 'crypto_fundamentals' in profile and 'error' not in profile['crypto_fundamentals']:
                    cf = profile['crypto_fundamentals']
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric('Current Price', f"${cf.get('current_price_usd', 0):,.2f}")
                    col2.metric('Market Cap', f"${cf.get('market_cap_usd', 0):,.0f}")
                    col3.metric('Market Cap Rank', f"#{cf.get('market_cap_rank', 'N/A')}")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric('24h Change', f"{cf.get('price_change_24h_pct', 0):.2f}%")
                    col2.metric('24h Volume', f"${cf.get('total_volume_24h', 0):,.0f}")
                    col3.metric('Circulating Supply', f"{cf.get('circulating_supply', 0):,.0f}")
                    
                    st.write('**Price History**')
                    col1, col2, col3 = st.columns(3)
                    col1.metric('7d Change', f"{cf.get('price_change_7d_pct', 0):.2f}%")
                    col2.metric('30d Change', f"{cf.get('price_change_30d_pct', 0):.2f}%")
                    col3.metric('ATH', f"${cf.get('all_time_high', 0):,.2f}")
                else:
                    st.error('Failed to fetch crypto data')
            else:
                profile = get_company_profile(ticker)
                
                if 'error' not in profile.get('basic_info', {}):
                    basic = profile['basic_info']
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric('Company', basic.get('company_name', 'N/A'))
                    col2.metric('Sector', basic.get('sector', 'N/A'))
                    col3.metric('Industry', basic.get('industry', 'N/A'))
                    
                    st.write('**Financial Metrics**')
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric('Market Cap', f"${basic.get('market_cap', 0):,.0f}")
                    col2.metric('P/E Ratio', f"{basic.get('pe_ratio', 0):.2f}")
                    col3.metric('Dividend Yield', f"{basic.get('dividend_yield', 0)*100:.2f}%")
                    col4.metric('Beta', f"{basic.get('beta', 0):.2f}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric('Revenue', f"${basic.get('revenue', 0):,.0f}")
                    col2.metric('Net Income', f"${basic.get('net_income', 0):,.0f}")
                    col3.metric('Total Debt', f"${basic.get('total_debt', 0):,.0f}")
                    col4.metric('Cash', f"${basic.get('cash_and_equivalents', 0):,.0f}")
                    
                    # Financial Health
                    st.write('**Financial Health**')
                    health = profile.get('financial_health', {})
                    col1, col2 = st.columns(2)
                    with col1:
                        score = health.get('health_score', 0)
                        st.metric('Health Score', f"{score}/100")
                    with col2:
                        for factor in health.get('factors', []):
                            st.write(factor)
                    
                    # Income Statement
                    if not profile.get('income_statement', pd.DataFrame()).empty:
                        st.write('**Income Statement**')
                        st.dataframe(profile['income_statement'], use_container_width=True)
                    
                    # SEC Filings
                    if not profile.get('sec_filings', pd.DataFrame()).empty:
                        st.write('**Recent SEC Filings**')
                        st.dataframe(profile['sec_filings'], use_container_width=True)
                else:
                    st.error('Failed to fetch company data')


# Tab 5: Investigator (FUNCTIONAL)
with tabs[5]:
    st.subheader('🕵️ Investigator Mode')
    st.write('Evidence-based investigation: separate confirmed **facts**, **correlations**, and **hypotheses**.')
    
    investigation_tab1, investigation_tab2, investigation_tab3 = st.tabs(['Automated Analysis', 'Manual Investigation', 'Investigation Report'])
    
    with investigation_tab1:
        st.write('**Automated Revenue & Fundamentals Analysis**')
        if st.button('Analyze Financials'):
            with st.spinner('Analyzing financial changes...'):
                fin_analysis = analyze_revenue_changes(ticker)
                if 'error' not in fin_analysis:
                    st.write('**Revenue & Margin Trends**')
                    for obs in fin_analysis.get('observations', []):
                        if '✓' in obs:
                            st.success(obs)
                        elif '✗' in obs:
                            st.error(obs)
                        else:
                            st.info(obs)
        
        st.write('**Volume & Price Anomalies**')
        if st.button('Detect Anomalies'):
            with st.spinner('Finding anomalies...'):
                anomalies = find_volume_price_anomalies(ticker)
                if not anomalies.empty:
                    st.dataframe(anomalies, use_container_width=True)
                    st.success(f'Found {len(anomalies)} anomalies (>{2.0}σ)')
                else:
                    st.info('No major anomalies detected')
    
    with investigation_tab2:
        st.write('**Build Your Investigation**')
        
        if 'investigation' not in st.session_state:
            st.session_state['investigation'] = Investigation(ticker, f"Analysis of {ticker}")
        
        inv = st.session_state['investigation']
        
        # Add fact
        with st.expander('➕ Add Fact'):
            fact_desc = st.text_input('What is the fact?')
            fact_source = st.text_input('Source of this fact')
            fact_conf = st.slider('Confidence level', 0.0, 1.0, 0.8)
            if st.button('Add Fact'):
                inv.add_fact(fact_desc, fact_source, fact_conf)
                st.success('Fact added!')
        
        # Add correlation
        with st.expander('🔗 Add Correlation'):
            event1 = st.text_input('First event/metric')
            event2 = st.text_input('Second event/metric')
            corr_strength = st.slider('Correlation strength', -1.0, 1.0, 0.0)
            corr_desc = st.text_area('Description of correlation')
            if st.button('Add Correlation'):
                inv.add_correlation(event1, event2, corr_strength, corr_desc)
                st.success('Correlation added!')
        
        # Add hypothesis
        with st.expander('💡 Add Hypothesis'):
            hyp_text = st.text_area('What is your hypothesis?')
            supporting = st.text_area('Supporting evidence (one per line)').split('\n')
            counter = st.text_area('Counter evidence (one per line)').split('\n')
            if st.button('Add Hypothesis'):
                inv.add_hypothesis(hyp_text, supporting, counter)
                st.success('Hypothesis added!')
        
        # Add event
        with st.expander('📅 Add Public Event'):
            event_date = st.date_input('Event date')
            event_text = st.text_input('What happened?')
            impact = st.selectbox('Impact area', ['Revenue', 'Margins', 'Debt', 'Competition', 'Regulation', 'Other'])
            expected = st.selectbox('Expected impact on price', ['UP', 'DOWN', 'UNKNOWN'])
            if st.button('Add Event'):
                inv.add_public_event(str(event_date), event_text, impact, expected)
                st.success('Event added!')
        
        # Conclusion
        with st.expander('📝 Write Conclusion'):
            conclusion = st.text_area('Your final conclusion based on evidence')
            if st.button('Save Conclusion'):
                inv.conclusion = conclusion
                st.success('Conclusion saved!')
    
    with investigation_tab3:
        st.write('**Investigation Summary**')
        summary = st.session_state.get('investigation', Investigation(ticker)).get_summary()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric('Facts', summary.get('facts_count', 0))
        col2.metric('Correlations', summary.get('correlations_count', 0))
        col3.metric('Hypotheses', summary.get('hypotheses_count', 0))
        col4.metric('Events', summary.get('public_events_count', 0))
        
        if st.button('Generate Report'):
            report = create_investigation_report(st.session_state.get('investigation', Investigation(ticker)))
            st.text(report)
            st.download_button('Download Report', report, f'{ticker}_investigation.txt')
