"""Evidence-based public information investigator.
Separates confirmed facts, correlations and hypotheses; does not make accusations.
"""
from __future__ import annotations
import pandas as pd

def analyze_revenue_changes(income: pd.DataFrame):
    if income is None or income.empty or "Total Revenue" not in income.columns: return []
    s=pd.to_numeric(income["Total Revenue"],errors="coerce").dropna().sort_index()
    return [{"period":str(idx),"revenue":float(v),"change_pct":None if i==0 else round((v/s.iloc[i-1]-1)*100,2)} for i,(idx,v) in enumerate(s.items())]

def find_volume_price_anomalies(df, volume_multiple=2.0, move_pct=2.0):
    if df is None or df.empty: return pd.DataFrame()
    x=df.copy(); x["vol_avg"]=x["Volume"].rolling(20,min_periods=10).mean(); x["return_pct"]=x["Close"].pct_change()*100
    mask=(x["Volume"]>x["vol_avg"]*volume_multiple)&(x["return_pct"].abs()>=move_pct)
    return x.loc[mask,["Close","Volume","vol_avg","return_pct"]]

def correlate_events_to_price(events, df, window=2):
    if not events or df is None or df.empty: return []
    idx=pd.to_datetime(df.index); out=[]
    for e in events:
        date=pd.to_datetime(e.get("date") or e.get("filing_date"),errors="coerce")
        if pd.isna(date): continue
        pos=idx.searchsorted(date)
        if pos>=len(df): continue
        before=max(0,pos-window); after=min(len(df)-1,pos+window)
        change=(df["Close"].iloc[after]/df["Close"].iloc[before]-1)*100 if df["Close"].iloc[before] else 0
        out.append({"date":str(date.date()),"event":e.get("event") or e.get("form","Public filing"),"price_window_change_pct":round(float(change),2),"classification":"CORRELATION — timing alone does not prove causation"})
    return out

def create_investigation_report(symbol, profile, price_df):
    filings=profile.get("sec_filings",pd.DataFrame())
    events=[] if filings.empty else [{"date":r["filing_date"],"event":f"SEC {r['form']} filing"} for _,r in filings.iterrows()]
    anomalies=find_volume_price_anomalies(price_df)
    correlations=correlate_events_to_price(events,price_df)
    return {"symbol":symbol,"confirmed_facts":["Financial metrics and filing dates are displayed from underlying providers.","SEC event records are treated as public filings, not causal explanations."],"correlations":correlations,"anomalies":[] if anomalies.empty else [{"time":str(i),"return_pct":round(float(r["return_pct"]),2),"volume_multiple":round(float(r["Volume"]/r["vol_avg"]),2)} for i,r in anomalies.tail(20).iterrows()],"hypotheses":["Use anomalies as leads for further research; they are not proof of institutional activity or misconduct."]}

class Investigation:
    def __init__(self, symbol): self.symbol=symbol; self.events=[]
    def add_event(self, date, event, evidence="user supplied / public source"): self.events.append({"date":date,"event":event,"evidence":evidence})
