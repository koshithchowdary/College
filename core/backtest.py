from core.footprint import enrich
from core.signal_engine import analyze
import pandas as pd

def run_backtest(df,warmup=60,holding=25):
    trades=[]
    for i in range(warmup,len(df)-1):
        d=analyze(enrich(df.iloc[:i+1]))
        if d['status'] not in ('BUY','SELL') or d['entry'] is None: continue
        future=df.iloc[i+1:min(i+holding,len(df))]; exit_price=future.iloc[-1].Close; result='TIME'
        for _,bar in future.iterrows():
            if d['status']=='BUY':
                if bar.Low<=d['stop']: exit_price=d['stop']; result='SL'; break
                if bar.High>=d['targets'][1]: exit_price=d['targets'][1]; result='TP2'; break
            else:
                if bar.High>=d['stop']: exit_price=d['stop']; result='SL'; break
                if bar.Low<=d['targets'][1]: exit_price=d['targets'][1]; result='TP2'; break
        pnl=(exit_price-d['entry'])/d['entry'] if d['status']=='BUY' else (d['entry']-exit_price)/d['entry']
        trades.append({'time':df.index[i],'side':d['status'],'result':result,'pnl_pct':pnl*100,'score':d['score']})
    t=pd.DataFrame(trades)
    if t.empty:return t,{'trades':0,'win_rate':0,'profit_factor':0,'net_pnl':0,'max_drawdown':0}
    eq=(1+t.pnl_pct/100).cumprod(); losses=-t.loc[t.pnl_pct<0,'pnl_pct'].sum(); wins=t.loc[t.pnl_pct>0,'pnl_pct'].sum()
    return t,{'trades':len(t),'win_rate':round((t.pnl_pct>0).mean()*100,2),'profit_factor':round(wins/losses,2) if losses else None,'net_pnl':round((eq.iloc[-1]-1)*100,2),'max_drawdown':round((eq/eq.cummax()-1).min()*100,2)}
