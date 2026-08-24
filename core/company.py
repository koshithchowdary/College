"""Company intelligence using public Yahoo Finance data and SEC EDGAR submissions."""
from __future__ import annotations
import requests, pandas as pd, yfinance as yf
from functools import lru_cache
SEC_HEADERS={"User-Agent":"AEGIS Intelligence research contact@example.com","Accept-Encoding":"gzip, deflate"}

@lru_cache(maxsize=1)
def _ticker_map():
    data=requests.get("https://www.sec.gov/files/company_tickers.json",headers=SEC_HEADERS,timeout=20).json()
    return {v["ticker"].upper():str(v["cik_str"]).zfill(10) for v in data.values()}

def get_sec_filings(symbol, limit=20):
    try:
        cik=_ticker_map().get(symbol.upper())
        if not cik: return pd.DataFrame(columns=["filing_date","form","accession","primary_document","url"])
        data=requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json",headers=SEC_HEADERS,timeout=20).json()
        recent=data.get("filings",{}).get("recent",{}); rows=[]
        for i,form in enumerate(recent.get("form",[])[:limit]):
            accession=recent["accessionNumber"][i]; doc=recent["primaryDocument"][i]
            rows.append({"filing_date":recent["filingDate"][i],"form":form,"accession":accession,"primary_document":doc,"url":f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-','')}/{doc}"})
        return pd.DataFrame(rows)
    except Exception: return pd.DataFrame(columns=["filing_date","form","accession","primary_document","url"])

def _frame(obj, names):
    if obj is None or obj.empty: return pd.DataFrame()
    out=[]
    for n in names:
        if n in obj.index: out.append(obj.loc[n].rename(n))
    return pd.DataFrame(out).T

def get_company_profile(symbol):
    t=yf.Ticker(symbol.upper()); info=t.info or {}
    basic={"company_name":info.get("longName") or info.get("shortName","N/A"),"sector":info.get("sector","N/A"),"industry":info.get("industry","N/A"),"website":info.get("website"),"market_cap":info.get("marketCap",0),"pe_ratio":info.get("trailingPE",0),"revenue":info.get("totalRevenue",0),"net_income":info.get("netIncomeToCommon",0),"total_debt":info.get("totalDebt",0),"cash":info.get("totalCash",0),"insider_ownership":info.get("heldPercentInsiders",0),"institutional_ownership":info.get("heldPercentInstitutions",0)}
    income=_frame(t.income_stmt,["Total Revenue","Gross Profit","Operating Income","Net Income"])
    balance=_frame(t.balance_sheet,["Total Assets","Current Assets","Total Debt","Stockholders Equity"])
    cash=_frame(t.cashflow,["Operating Cash Flow","Free Cash Flow","Capital Expenditure"])
    factors=[]; score=50
    de=info.get("debtToEquity") or 0
    if de and de<100: score+=10; factors.append("Moderate or low reported debt-to-equity")
    elif de>200: score-=10; factors.append("High reported debt-to-equity")
    margin=info.get("profitMargins") or 0
    if margin>0.15: score+=10; factors.append("Strong reported profit margin")
    elif margin<0: score-=10; factors.append("Negative reported profit margin")
    return {"basic_info":basic,"income_statement":income,"balance_sheet":balance,"cash_flow":cash,"financial_health":{"health_score":max(0,min(100,score)),"factors":factors},"management":{"ceo":info.get("companyOfficers",[]),"insider_ownership":basic["insider_ownership"],"institutional_ownership":basic["institutional_ownership"]},"sec_filings":get_sec_filings(symbol)}

def get_crypto_fundamentals(symbol):
    s=symbol.upper().replace("-USD","").replace("USDT","")
    aliases={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple"}
    coin=aliases.get(s,s.lower())
    r=requests.get(f"https://api.coingecko.com/api/v3/coins/{coin}",params={"localization":"false","tickers":"false","community_data":"false","developer_data":"false"},timeout=20); r.raise_for_status(); d=r.json(); m=d.get("market_data",{})
    return {"name":d.get("name"),"current_price_usd":m.get("current_price",{}).get("usd"),"market_cap_usd":m.get("market_cap",{}).get("usd"),"market_cap_rank":d.get("market_cap_rank"),"price_change_24h_pct":m.get("price_change_percentage_24h"),"total_volume_24h":m.get("total_volume",{}).get("usd"),"circulating_supply":m.get("circulating_supply"),"all_time_high":m.get("ath",{}).get("usd")}
