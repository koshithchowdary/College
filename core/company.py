"""Company Intelligence Module: Financial data, SEC filings, management & ownership."""

import requests
import pandas as pd
from datetime import datetime
import yfinance as yf

# Alpha Vantage API for fundamental data (requires API key - get free from https://www.alphavantage.co/)
ALPHA_VANTAGE_API_KEY = "demo"  # Replace with your free API key from alphavantage.co

# SEC Edgar for SEC filings data (no API key needed - public API)
SEC_EDGAR_BASE = "https://data.sec.gov/api/xbrl"


def get_sec_filings(symbol: str, filing_type: str = "10-K") -> pd.DataFrame:
    """
    Fetch SEC filings from SEC Edgar.
    
    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        filing_type: Type of filing ('10-K', '10-Q', '8-K', etc.)
    
    Returns:
        DataFrame with filing information
    """
    try:
        # Using SEC Edgar XBRL API (public, no key needed)
        # This fetches company filings data
        url = f"https://www.sec.gov/cgi-bin/browse-edgar"
        params = {
            "action": "getcompany",
            "CIK": symbol,
            "type": filing_type,
            "dateb": "",
            "owner": "exclude",
            "count": 10,
            "output": "json"
        }
        
        headers = {'User-Agent': 'AEGIS Intelligence (aegis@example.com)'}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if "filings" not in data or "files" not in data["filings"]:
            return pd.DataFrame(columns=["date", "filing_type", "url", "accession"])
        
        filings = []
        for filing in data["filings"]["files"][:5]:
            filings.append({
                "date": filing.get("filingDate", "N/A"),
                "filing_type": filing.get("form", "N/A"),
                "url": f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={symbol}&accession_number={filing.get('accessionNumber', '')}&xbrl_type=v",
                "accession": filing.get("accessionNumber", "N/A")
            })
        
        return pd.DataFrame(filings)
    
    except Exception as e:
        print(f"SEC filings fetch error: {e}")
        return pd.DataFrame(columns=["date", "filing_type", "url", "accession"])


def get_financial_data(symbol: str) -> dict:
    """
    Fetch company financial data from Yahoo Finance / Alpha Vantage.
    
    Args:
        symbol: Stock ticker (e.g., 'AAPL')
    
    Returns:
        Dictionary with financial metrics
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        financials = {
            "symbol": symbol,
            "company_name": info.get("longName", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "revenue": info.get("totalRevenue", 0),
            "gross_profit": info.get("grossProfit", 0),
            "operating_income": info.get("operatingCashflow", 0),
            "net_income": info.get("netIncomeToCommon", 0),
            "total_debt": info.get("totalDebt", 0),
            "cash_and_equivalents": info.get("totalCash", 0),
            "current_ratio": info.get("currentRatio", 0),
            "debt_to_equity": info.get("debtToEquity", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "pb_ratio": info.get("priceToBook", 0),
            "dividend_yield": info.get("dividendYield", 0),
            "eps": info.get("trailingEps", 0),
            "52_week_high": info.get("fiftyTwoWeekHigh", 0),
            "52_week_low": info.get("fiftyTwoWeekLow", 0),
            "beta": info.get("beta", 0),
        }
        
        return financials
    
    except Exception as e:
        print(f"Financial data fetch error: {e}")
        return {
            "symbol": symbol,
            "error": str(e),
            "company_name": "N/A",
            "market_cap": 0,
            "revenue": 0,
            "net_income": 0,
            "total_debt": 0,
            "cash_and_equivalents": 0,
        }


def get_income_statement(symbol: str) -> pd.DataFrame:
    """Fetch income statement data (Revenue, Gross Profit, Operating Income, Net Income)."""
    try:
        ticker = yf.Ticker(symbol)
        income_stmt = ticker.income_stmt
        
        if income_stmt.empty:
            return pd.DataFrame()
        
        # Get last 4 quarters
        data = {
            "period": [str(date.date()) for date in income_stmt.columns],
            "revenue": income_stmt.loc["Total Revenue"].values if "Total Revenue" in income_stmt.index else [0] * len(income_stmt.columns),
            "gross_profit": income_stmt.loc["Gross Profit"].values if "Gross Profit" in income_stmt.index else [0] * len(income_stmt.columns),
            "operating_income": income_stmt.loc["Operating Income"].values if "Operating Income" in income_stmt.index else [0] * len(income_stmt.columns),
            "net_income": income_stmt.loc["Net Income"].values if "Net Income" in income_stmt.index else [0] * len(income_stmt.columns),
        }
        
        return pd.DataFrame(data)
    
    except Exception as e:
        print(f"Income statement fetch error: {e}")
        return pd.DataFrame()


def get_balance_sheet(symbol: str) -> pd.DataFrame:
    """Fetch balance sheet data (Assets, Liabilities, Equity)."""
    try:
        ticker = yf.Ticker(symbol)
        balance_sheet = ticker.balance_sheet
        
        if balance_sheet.empty:
            return pd.DataFrame()
        
        data = {
            "period": [str(date.date()) for date in balance_sheet.columns],
            "total_assets": balance_sheet.loc["Total Assets"].values if "Total Assets" in balance_sheet.index else [0] * len(balance_sheet.columns),
            "current_assets": balance_sheet.loc["Current Assets"].values if "Current Assets" in balance_sheet.index else [0] * len(balance_sheet.columns),
            "total_liabilities": balance_sheet.loc["Total Liabilities Net Minority Interest"].values if "Total Liabilities Net Minority Interest" in balance_sheet.index else [0] * len(balance_sheet.columns),
            "total_equity": balance_sheet.loc["Total Equity Gross Minority Interest"].values if "Total Equity Gross Minority Interest" in balance_sheet.index else [0] * len(balance_sheet.columns),
        }
        
        return pd.DataFrame(data)
    
    except Exception as e:
        print(f"Balance sheet fetch error: {e}")
        return pd.DataFrame()


def get_cash_flow(symbol: str) -> pd.DataFrame:
    """Fetch cash flow statement (Operating, Investing, Financing Cash Flows)."""
    try:
        ticker = yf.Ticker(symbol)
        cash_flow = ticker.cashflow
        
        if cash_flow.empty:
            return pd.DataFrame()
        
        data = {
            "period": [str(date.date()) for date in cash_flow.columns],
            "operating_cash_flow": cash_flow.loc["Operating Cash Flow"].values if "Operating Cash Flow" in cash_flow.index else [0] * len(cash_flow.columns),
            "investing_cash_flow": cash_flow.loc["Investing Cash Flow"].values if "Investing Cash Flow" in cash_flow.index else [0] * len(cash_flow.columns),
            "financing_cash_flow": cash_flow.loc["Financing Cash Flow"].values if "Financing Cash Flow" in cash_flow.index else [0] * len(cash_flow.columns),
            "free_cash_flow": cash_flow.loc["Free Cash Flow"].values if "Free Cash Flow" in cash_flow.index else [0] * len(cash_flow.columns),
        }
        
        return pd.DataFrame(data)
    
    except Exception as e:
        print(f"Cash flow fetch error: {e}")
        return pd.DataFrame()


def get_management_info(symbol: str) -> dict:
    """Fetch management and insider information."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        management = {
            "ceo": info.get("compensationAsOfEpochDate", "N/A"),
            "number_of_analysts": info.get("numberOfAnalystRatings", 0),
            "recommendation_key": info.get("recommendationKey", "N/A"),
            "board_members": "Not available through yfinance",
            "insider_ownership": info.get("heldPercentInsiders", 0),
            "institutional_ownership": info.get("heldPercentInstitutions", 0),
        }
        
        return management
    
    except Exception as e:
        print(f"Management info fetch error: {e}")
        return {"error": str(e)}


def calculate_financial_health_score(symbol: str) -> dict:
    """
    Calculate overall financial health score (0-100).
    
    Factors:
    - Debt to Equity ratio
    - Current Ratio
    - ROE (Return on Equity)
    - Profit Margin
    - Free Cash Flow trend
    """
    try:
        data = get_financial_data(symbol)
        
        score = 50  # Base score
        factors = []
        
        # Debt to Equity analysis
        if data.get("debt_to_equity", 0) > 0:
            if data["debt_to_equity"] < 0.5:
                score += 15
                factors.append("✓ Low debt-to-equity ratio (financially conservative)")
            elif data["debt_to_equity"] < 1.5:
                score += 5
                factors.append("⚠ Moderate debt-to-equity ratio")
            else:
                score -= 10
                factors.append("✗ High debt-to-equity ratio (elevated financial risk)")
        
        # Liquidity analysis
        if data.get("current_ratio", 0) > 0:
            if data["current_ratio"] > 1.5:
                score += 10
                factors.append("✓ Strong liquidity position")
            elif data["current_ratio"] > 1.0:
                score += 5
                factors.append("⚠ Adequate liquidity")
            else:
                score -= 10
                factors.append("✗ Weak liquidity position")
        
        # Valuation
        if data.get("pe_ratio", 0) > 0:
            if data["pe_ratio"] < 15:
                score += 8
                factors.append("✓ Attractive valuation (low P/E)")
            elif data["pe_ratio"] < 25:
                factors.append("⚠ Fair valuation (moderate P/E)")
            else:
                score -= 5
                factors.append("⚠ High valuation (high P/E)")
        
        # Dividend
        if data.get("dividend_yield", 0) > 0:
            if data["dividend_yield"] > 0.02:
                score += 7
                factors.append(f"✓ Attractive dividend yield ({data['dividend_yield']*100:.2f}%)")
        
        score = max(0, min(100, score))
        
        return {
            "health_score": score,
            "factors": factors,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"Health score calculation error: {e}")
        return {"health_score": 0, "factors": [str(e)]}


def get_company_profile(symbol: str) -> dict:
    """Get comprehensive company profile."""
    profile = {
        "basic_info": get_financial_data(symbol),
        "income_statement": get_income_statement(symbol),
        "balance_sheet": get_balance_sheet(symbol),
        "cash_flow": get_cash_flow(symbol),
        "management": get_management_info(symbol),
        "financial_health": calculate_financial_health_score(symbol),
        "sec_filings": get_sec_filings(symbol),
    }
    return profile
