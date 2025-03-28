import pandas as pd
import numpy as np
from datetime import datetime

def format_timedelta(td):
    """Format a timedelta into a readable string with years, months, days, hours, minutes and seconds"""
    if pd.isnull(td):
        return "0 secs"
        
    # Extract components
    total_days = td.days
    seconds = td.seconds
    
    # Calculate years, months, days
    years, remaining_days = divmod(total_days, 365)
    months, days = divmod(remaining_days, 30)
    
    # Calculate hours, minutes from seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Build the string parts
    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months > 0:
        parts.append(f"{months} month{'s' if months != 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} min{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:  # Always include seconds if no other parts
        parts.append(f"{seconds} sec{'s' if seconds != 1 else ''}")
    
    # Join with commas and 'and' for the last part
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + " and " + parts[-1]
    elif parts:
        return parts[0]
    else:
        return "0 secs"

def calculate_performance_summary(trades_df, initial_balance=10000, risk_per_trade=0.01):
    """
    Calculate performance metrics from a dataframe of trades
    
    Parameters:
    -----------
    trades_df : pd.DataFrame
        DataFrame containing trade information including 'pnl_perc' or 'perc_chg',
        'entry_time' and 'exit_time'
    initial_balance : float
        Initial account balance to start with
    risk_per_trade : float
        Fraction of account to risk on each trade (0.01 = 1%)
        
    Returns:
    --------
    dict
        Dictionary containing performance metrics
    """
    if trades_df.empty:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "final_balance": initial_balance,
            "max_drawdown_percent": 0,
            "avg_trade_duration": "0 secs",
            "total_strategy_duration": "0 secs"
        }
    
    # Standardize column name for pnl percentage
    pnl_col = 'perc_chg' if 'perc_chg' in trades_df.columns else 'pnl_perc'
    
    # Initialize metrics
    balance = initial_balance
    wins = 0
    losses = 0
    total_profit = 0
    total_loss = 0
    max_balance = balance
    max_drawdown = 0
    
    # Calculate trade durations
    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
    trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
    trades_df['duration'] = trades_df['exit_time'] - trades_df['entry_time']
    
    # Calculate average trade duration
    avg_duration = trades_df['duration'].mean()
    
    # Calculate total strategy duration
    if len(trades_df) > 0:
        strategy_start = trades_df['entry_time'].min()
        strategy_end = trades_df['exit_time'].max()
        total_duration = strategy_end - strategy_start
    else:
        total_duration = pd.Timedelta(0)
    
    # Process each trade
    for _, trade in trades_df.iterrows():
        # Calculate position size based on risk
        position_size = balance * risk_per_trade
        
        # Calculate profit/loss in currency
        pnl_percent = trade[pnl_col]
        pnl_amount = position_size * pnl_percent
        
        # Update balance
        balance += pnl_amount
        
        # Update win/loss counters
        if pnl_percent > 0:
            wins += 1
            total_profit += pnl_percent
        else:
            losses += 1
            total_loss += abs(pnl_percent)
        
        # Update max balance and drawdown
        if balance > max_balance:
            max_balance = balance
        
        drawdown = (max_balance - balance) / max_balance if max_balance > 0 else 0
        max_drawdown = max(max_drawdown, drawdown)
    
    # Calculate final metrics
    total_trades = wins + losses
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    
    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "final_balance": balance,
        "max_drawdown_percent": max_drawdown * 100,
        "avg_trade_duration": format_timedelta(avg_duration),
        "total_strategy_duration": format_timedelta(total_duration)
    }