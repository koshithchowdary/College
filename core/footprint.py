import numpy as np

def enrich(df):
    x=df.copy(); x['body']=(x.Close-x.Open).abs(); x['range']=(x.High-x.Low).replace(0,np.nan)
    x['body_ratio']=(x.body/x['range']).fillna(0); x['vol_ma']=x.Volume.rolling(20,min_periods=5).mean().replace(0,np.nan)
    x['relative_volume']=(x.Volume/x.vol_ma).replace([np.inf,-np.inf],0).fillna(1)
    x['tr']=np.maximum(x.High-x.Low,np.maximum((x.High-x.Close.shift()).abs(),(x.Low-x.Close.shift()).abs()))
    x['atr']=x.tr.rolling(14,min_periods=5).mean().bfill()
    direction=np.where(x.Close>=x.Open,1,-1); x['delta_proxy']=x.Volume*direction*(x.body_ratio*.8+.2); x['cvd_proxy']=x.delta_proxy.cumsum()
    x['prior_20_high']=x.High.rolling(20).max().shift(1); x['prior_20_low']=x.Low.rolling(20).min().shift(1)
    x['liquidity_sweep_high']=(x.High>x.prior_20_high)&(x.Close<x.prior_20_high)
    x['liquidity_sweep_low']=(x.Low<x.prior_20_low)&(x.Close>x.prior_20_low)
    x['displacement']=(x.body>1.5*x.atr)&(x.body_ratio>.65)&(x.relative_volume>1.1)
    x['ema20']=x.Close.ewm(span=20,adjust=False).mean(); x['ema50']=x.Close.ewm(span=50,adjust=False).mean()
    x['trend']=np.where(x.ema20>x.ema50,'bullish',np.where(x.ema20<x.ema50,'bearish','neutral'))
    return x
