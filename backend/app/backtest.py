import pandas as pd

def create_empty_result():
    """Create empty DataFrame for when no signals are present"""
    return pd.DataFrame({
        "entry_time": [0],
        "entry_price": [0],
        "tp_target": [0],
        "sl_target": [0],
        "exit_time": [0],
        "exit_price": [0],
        "pnl": [0],
        "equity": [0],
        "pnl_perc": [0]
    })

def process_exit_signal(current_trade, exit_time, exit_price, percentage_change):
    """Create a trade dictionary for a completed trade"""
    return {
        "entry_time": current_trade["entry_time"],
        "entry_price": current_trade["entry_price"],
        "side": current_trade["side"],
        "tp_target": current_trade["tp_price"],
        "sl_target": current_trade["sl_price"],
        "sl_distance": current_trade["sl_distance"],
        "exit_time": exit_time,
        "exit_price": exit_price,
        "perc_chg": percentage_change,
    }

def handle_buy_exit(i, df, current_buy_trade, in_buy_position, buy_trades, tp, sl):
    """Process potential exits for an active buy trade"""
    if not in_buy_position:
        return current_buy_trade, in_buy_position, buy_trades
        
    # Check stop loss condition
    if df.iloc[i].low < current_buy_trade["sl_price"]:
        percentage_change = -1 * sl/100
        buy_trades.append(process_exit_signal(
            current_buy_trade, 
            df.iloc[i].name, 
            current_buy_trade["sl_price"], 
            percentage_change
        ))
        return {}, False, buy_trades
        
    # Check take profit condition
    if df.iloc[i].high > current_buy_trade["tp_price"]:
        percentage_change = tp/100
        buy_trades.append(process_exit_signal(
            current_buy_trade, 
            df.iloc[i].name, 
            current_buy_trade["tp_price"], 
            percentage_change
        ))
        return {}, False, buy_trades
    
    return current_buy_trade, in_buy_position, buy_trades

def handle_sell_exit(i, df, current_sell_trade, in_sell_position, sell_trades, tp, sl):
    """Process potential exits for an active sell trade"""
    if not in_sell_position:
        return current_sell_trade, in_sell_position, sell_trades
        
    # Check stop loss condition
    if df.iloc[i].high > current_sell_trade["sl_price"]:
        percentage_change = -1 * sl/100
        sell_trades.append(process_exit_signal(
            current_sell_trade, 
            df.iloc[i].name, 
            current_sell_trade["sl_price"], 
            percentage_change
        ))
        return {}, False, sell_trades
        
    # Check take profit condition
    if df.iloc[i].low < current_sell_trade["tp_price"]:
        percentage_change = tp/100
        sell_trades.append(process_exit_signal(
            current_sell_trade, 
            df.iloc[i].name, 
            current_sell_trade["tp_price"], 
            percentage_change
        ))
        return {}, False, sell_trades
    
    return current_sell_trade, in_sell_position, sell_trades

def handle_buy_entry(i, df, in_buy_position, tp, sl):
    """Process potential buy entries"""
    if not in_buy_position and df.iloc[i].buy_signal:
        entry_price = df.iloc[i].entry_price
        return {
            "entry_price": entry_price,
            "entry_time": df.iloc[i + 1].name,
            "side": "long",
            "tp_price": entry_price * (1 + tp/100),
            "sl_price": entry_price * (1 - sl/100),
            "sl_distance": entry_price - (entry_price * (1 - sl/100)),
        }, True
    return {}, in_buy_position

def handle_sell_entry(i, df, in_sell_position, tp, sl):
    """Process potential sell entries"""
    if not in_sell_position and df.iloc[i].sell_signal:
        entry_price = df.iloc[i].entry_price
        return {
            "entry_price": entry_price,
            "entry_time": df.iloc[i + 1].name,
            "side": "short",
            "tp_price": entry_price * (1 - tp/100),
            "sl_price": entry_price * (1 + sl/100),
            "sl_distance": (entry_price * (1 + sl/100)) - entry_price,
        }, True
    return {}, in_sell_position

def backtest(df: pd.DataFrame, tp: float, sl: float):
    """Main backtesting function that walks through the dataframe and generates trades"""
    # Error handle for no signals
    if len(df[df.buy_signal > 0]) == 0 and len(df[df.sell_signal > 0]) == 0:
        return create_empty_result()

    in_sell_position = False
    in_buy_position = False
    current_buy_trade = {}
    current_sell_trade = {}
    buy_trades = []
    sell_trades = []

    for i in range(len(df) - 1):
        # Process exits (check first to avoid entering and exiting on the same bar)
        current_buy_trade, in_buy_position, buy_trades = handle_buy_exit(
            i, df, current_buy_trade, in_buy_position, buy_trades, tp, sl
        )
        
        current_sell_trade, in_sell_position, sell_trades = handle_sell_exit(
            i, df, current_sell_trade, in_sell_position, sell_trades, tp, sl
        )
        
        # Process entries only if not in position
        if not in_buy_position:
            current_buy_trade, in_buy_position = handle_buy_entry(i, df, in_buy_position, tp, sl)
            
        if not in_sell_position:
            current_sell_trade, in_sell_position = handle_sell_entry(i, df, in_sell_position, tp, sl)

    # Combine and sort all trades
    all_trades = pd.DataFrame(buy_trades + sell_trades)
    if len(all_trades) > 0:
        return all_trades.sort_values(by='entry_time').reset_index(drop=True)
    return create_empty_result()