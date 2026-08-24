"""Enhanced Backtest Module with UI integration - Historical trading performance analysis."""

from core.footprint import enrich
from core.signal_engine import analyze
import pandas as pd
import numpy as np


def run_backtest(df, warmup=60, holding=25):
    """
    Run historical backtest on price data.
    
    Args:
        df: DataFrame with OHLCV data
        warmup: Minimum candles before first trade
        holding: Maximum candles to hold each trade
    
    Returns:
        trades DataFrame, performance metrics dictionary
    """
    trades = []
    
    for i in range(warmup, len(df) - 1):
        d = analyze(enrich(df.iloc[:i+1]))
        
        if d['status'] not in ('BUY', 'SELL') or d['entry'] is None:
            continue
        
        future = df.iloc[i+1:min(i+holding, len(df))]
        exit_price = future.iloc[-1].Close
        result = 'TIME'
        
        for _, bar in future.iterrows():
            if d['status'] == 'BUY':
                if bar.Low <= d['stop']:
                    exit_price = d['stop']
                    result = 'SL'
                    break
                if bar.High >= d['targets'][1]:
                    exit_price = d['targets'][1]
                    result = 'TP2'
                    break
            else:
                if bar.High >= d['stop']:
                    exit_price = d['stop']
                    result = 'SL'
                    break
                if bar.Low <= d['targets'][1]:
                    exit_price = d['targets'][1]
                    result = 'TP2'
                    break
        
        pnl = (exit_price - d['entry']) / d['entry'] if d['status'] == 'BUY' else (d['entry'] - exit_price) / d['entry']
        trades.append({
            'time': df.index[i],
            'side': d['status'],
            'result': result,
            'pnl_pct': pnl * 100,
            'score': d['score'],
            'entry': d['entry'],
            'exit': exit_price
        })
    
    t = pd.DataFrame(trades)
    
    if t.empty:
        return t, {
            'trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'net_pnl': 0,
            'max_drawdown': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'consecutive_wins': 0,
            'consecutive_losses': 0
        }
    
    # Calculate metrics
    eq = (1 + t.pnl_pct / 100).cumprod()
    wins = t[t.pnl_pct > 0]['pnl_pct'].sum()
    losses = abs(t[t.pnl_pct < 0]['pnl_pct'].sum())
    
    winning_trades = t[t.pnl_pct > 0]
    losing_trades = t[t.pnl_pct < 0]
    
    avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0
    
    # Consecutive wins/losses
    consecutive_wins = 0
    consecutive_losses = 0
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    
    for pnl in t['pnl_pct'].values:
        if pnl > 0:
            consecutive_wins += 1
            consecutive_losses = 0
            max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
        else:
            consecutive_losses += 1
            consecutive_wins = 0
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
    
    metrics = {
        'trades': len(t),
        'win_rate': round((t.pnl_pct > 0).mean() * 100, 2),
        'profit_factor': round(wins / losses, 2) if losses > 0 else float('inf'),
        'net_pnl': round((eq.iloc[-1] - 1) * 100, 2),
        'max_drawdown': round(((eq.cummax() - eq) / eq.cummax()).max() * 100, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'best_trade': round(t['pnl_pct'].max(), 2),
        'worst_trade': round(t['pnl_pct'].min(), 2),
        'consecutive_wins': max_consecutive_wins,
        'consecutive_losses': max_consecutive_losses,
        'total_wins': len(winning_trades),
        'total_losses': len(losing_trades)
    }
    
    return t, metrics


def get_trade_analysis(trades_df):
    """
    Get detailed analysis of trades by exit reason.
    
    Args:
        trades_df: DataFrame of trades from backtest
    
    Returns:
        Dictionary with trade analysis
    """
    if trades_df.empty:
        return {}
    
    analysis = {}
    
    for result in trades_df['result'].unique():
        subset = trades_df[trades_df['result'] == result]
        analysis[result] = {
            'count': len(subset),
            'avg_pnl': round(subset['pnl_pct'].mean(), 2),
            'win_rate': round((subset['pnl_pct'] > 0).mean() * 100, 2),
            'total_pnl': round(subset['pnl_pct'].sum(), 2)
        }
    
    return analysis


def get_trade_by_score(trades_df):
    """
    Analyze trades grouped by confidence score.
    
    Args:
        trades_df: DataFrame of trades
    
    Returns:
        Dictionary with score-based analysis
    """
    if trades_df.empty:
        return {}
    
    # Group by score ranges
    trades_df_copy = trades_df.copy()
    trades_df_copy['score_range'] = pd.cut(trades_df_copy['score'], bins=[0, 50, 70, 85, 100], labels=['<50', '50-70', '70-85', '85+'])
    
    analysis = {}
    for score_range in trades_df_copy['score_range'].unique():
        subset = trades_df_copy[trades_df_copy['score_range'] == score_range]
        if len(subset) > 0:
            analysis[str(score_range)] = {
                'count': len(subset),
                'avg_pnl': round(subset['pnl_pct'].mean(), 2),
                'win_rate': round((subset['pnl_pct'] > 0).mean() * 100, 2),
            }
    
    return analysis


def get_side_analysis(trades_df):
    """
    Compare BUY vs SELL trade performance.
    
    Args:
        trades_df: DataFrame of trades
    
    Returns:
        Dictionary comparing sides
    """
    if trades_df.empty:
        return {}
    
    analysis = {}
    
    for side in ['BUY', 'SELL']:
        subset = trades_df[trades_df['side'] == side]
        if len(subset) > 0:
            analysis[side] = {
                'count': len(subset),
                'avg_pnl': round(subset['pnl_pct'].mean(), 2),
                'win_rate': round((subset['pnl_pct'] > 0).mean() * 100, 2),
                'total_pnl': round(subset['pnl_pct'].sum(), 2)
            }
    
    return analysis


def calculate_kelly_criterion(trades_df):
    """
    Calculate Kelly Criterion for optimal position sizing.
    Formula: f* = (bp - q) / b
    where: b = odds, p = win probability, q = loss probability
    
    Args:
        trades_df: DataFrame of trades
    
    Returns:
        Kelly percentage (0-100)
    """
    if trades_df.empty or len(trades_df) < 2:
        return 0
    
    win_rate = (trades_df['pnl_pct'] > 0).mean()
    loss_rate = 1 - win_rate
    
    if win_rate == 0 or loss_rate == 0:
        return 0
    
    avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean()
    avg_loss = abs(trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean())
    
    if avg_loss == 0:
        return 0
    
    b = avg_win / avg_loss  # odds
    kelly = (b * win_rate - loss_rate) / b
    
    # Kelly is theoretical optimal, practical use 25-50% of it
    return max(0, min(100, kelly * 100 * 0.25))


def get_equity_curve(trades_df):
    """
    Calculate cumulative equity curve.
    
    Args:
        trades_df: DataFrame of trades
    
    Returns:
        DataFrame with time and cumulative equity
    """
    if trades_df.empty:
        return pd.DataFrame()
    
    trades_df_copy = trades_df.copy()
    trades_df_copy['cumulative_return'] = (1 + trades_df_copy['pnl_pct'] / 100).cumprod()
    
    return trades_df_copy[['time', 'cumulative_return']].set_index('time')
