import pandas as pd
import pandas_ta as ta
import numpy as np

df = pd.read_csv('../Binance_BTCUSDT_1min.csv')
df = df.iloc[:,:6]
df.columns=['timestamp','open', 'high', 'low', 'close', 'volume']
df.reset_index(drop=True, inplace=True)
df.timestamp = pd.to_datetime(df.timestamp)
df = df.set_index('timestamp')

def resample_df(df, freq):
    resampled_open = df.open.resample(freq).first()
    resampled_high = df.high.resample(freq).max()
    resampled_low = df.low.resample(freq).min()
    resampled_close = df.close.resample(freq).last()
    resampled_volume = df.volume.resample(freq).sum()
    new_df = pd.concat([resampled_open, resampled_high, resampled_low, resampled_close, resampled_volume], axis=1)
    new_df.dropna(inplace=True)
    return new_df

def calc_entry_price(new_df):
    new_df['entry_price'] = new_df.open.shift(-1)

def calc_fast_ma(new_df, fast_ma_length):
    new_df['fast_ma'] = ta.sma(new_df['close'], fast_ma_length)
def calc_slow_ma(new_df, slow_ma_length):
    new_df['slow_ma'] = ta.sma(new_df['close'], slow_ma_length)

def calc_conditions(new_df):
    new_df['buy_conditions'] = np.where(((new_df.close < new_df.fast_ma) & (new_df.close > new_df.slow_ma)), True, False)
    new_df['sell_conditions'] = np.where(((new_df.close > new_df.fast_ma) & (new_df.close < new_df.slow_ma)), True, False)

def calculate_signals(new_df):
    new_df['buy_signal'] = np.where(((new_df['buy_conditions'].shift(1) < 1) & (new_df['buy_conditions'] > 0)), True, False)
    new_df['sell_signal'] = np.where(((new_df['sell_conditions'].shift(1) < 1) & (new_df['sell_conditions'] > 0)), True, False)

def backtest_trades(df, freq, fast_ma_length, slow_ma_length, tp, sl):

    new_df = resample_df(df, freq)
    calc_entry_price(new_df)
    calc_fast_ma(new_df, fast_ma_length)
    calc_slow_ma(new_df, slow_ma_length)
    calc_conditions(new_df)
    calculate_signals(new_df)
    new_df.dropna(inplace=True)

    
    if len(new_df[new_df.buy_signal > 0]) == 0 and len(new_df[new_df.sell_signal > 0]) == 0:
        empty_result = pd.DataFrame({
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
        return empty_result

    # Initialize Variables
    in_sell_position = False
    in_buy_position = False
    buy_trades = []
    current_buy_trade = {}
    sell_trades = []
    current_sell_trade = {}

    for i in range(len(new_df) - 1):
        # Check exit conditions for buy position
        if in_buy_position:
            if new_df.iloc[i].low < current_buy_trade["sl_price"]:
                current_buy_trade["exit_price"] = current_buy_trade["sl_price"]
                pnl_perc = -1 * sl/100
                buy_trades.append({
                    "entry_time": current_buy_trade["entry_time"],
                    "entry_price": current_buy_trade["entry_price"],
                    "side": current_buy_trade["side"],
                    "tp_target": current_buy_trade["tp_price"],
                    "sl_target": current_buy_trade["sl_price"],
                    "sl_distance":current_buy_trade["sl_distance"],
                    "exit_time": new_df.iloc[i].name,
                    "exit_price": current_buy_trade["sl_price"],
                    "pnl_perc": pnl_perc,
                })
                current_buy_trade = {}
                in_buy_position = False

            elif new_df.iloc[i].high > current_buy_trade["tp_price"]:
                current_buy_trade["exit_price"] = current_buy_trade["tp_price"]
                pnl_perc = tp/100
                buy_trades.append({
                    "entry_time": current_buy_trade["entry_time"],
                    "entry_price": current_buy_trade["entry_price"],
                    "side": current_buy_trade["side"],
                    "tp_target": current_buy_trade["tp_price"],
                    "sl_target": current_buy_trade["sl_price"],
                    "sl_distance":current_buy_trade["sl_distance"],
                    "exit_time": new_df.iloc[i].name,
                    "exit_price": current_buy_trade["tp_price"],
                    "pnl_perc": pnl_perc,
                })
                current_buy_trade = {}
                in_buy_position = False

        # Check exit conditions for sell position
        if in_sell_position:
            if new_df.iloc[i].high > current_sell_trade["sl_price"]:
                current_sell_trade["exit_price"] = current_sell_trade["sl_price"]
                pnl_perc = -1 * sl/100
                sell_trades.append({
                    "entry_time": current_sell_trade["entry_time"],
                    "entry_price": current_sell_trade["entry_price"],
                    "side": current_sell_trade["side"],
                    "tp_target": current_sell_trade["tp_price"],
                    "sl_target": current_sell_trade["sl_price"],
                    "sl_distance":current_sell_trade["sl_distance"],
                    "exit_time": new_df.iloc[i].name,
                    "exit_price": current_sell_trade["sl_price"],
                    "pnl_perc": pnl_perc,
                })
                current_sell_trade = {}
                in_sell_position = False

            elif new_df.iloc[i].low < current_sell_trade["tp_price"]:
                current_sell_trade["exit_price"] = current_sell_trade["tp_price"]
                pnl_perc = tp/100
                sell_trades.append({
                    "entry_time": current_sell_trade["entry_time"],
                    "entry_price": current_sell_trade["entry_price"],
                    "side": current_sell_trade["side"],
                    "tp_target": current_sell_trade["tp_price"],
                    "sl_target": current_sell_trade["sl_price"],
                    "sl_distance":current_sell_trade["sl_distance"],
                    "exit_time": new_df.iloc[i].name,
                    "exit_price": current_sell_trade["tp_price"],
                    "pnl_perc": pnl_perc,
                })
                current_sell_trade = {}
                in_sell_position = False

        # Check entry conditions for buy position
        if not in_buy_position:
            if new_df.iloc[i].buy_signal:
                current_buy_trade["entry_price"] = new_df.iloc[i].entry_price
                current_buy_trade["entry_time"] = new_df.iloc[i + 1].name
                current_buy_trade["side"] = "long"
                current_buy_trade["tp_price"] = new_df.iloc[i].entry_price * (1 + tp/100)
                current_buy_trade["sl_price"] = new_df.iloc[i].entry_price * (1 - sl/100)
                current_buy_trade["sl_distance"] = new_df.iloc[i].entry_price - new_df.iloc[i].entry_price * (1 - sl/100)
                in_buy_position = True

        # Check entry conditions for sell position
        if not in_sell_position:
            if new_df.iloc[i].sell_signal:
                current_sell_trade["entry_price"] = new_df.iloc[i].entry_price
                current_sell_trade["entry_time"] = new_df.iloc[i + 1].name
                current_sell_trade["side"] = "short"
                current_sell_trade["tp_price"] = new_df.iloc[i].entry_price * (1 - tp/100)
                current_sell_trade["sl_price"] = new_df.iloc[i].entry_price * (1 + sl/100)
                #this was just a test for error --> see the buy conditions
                current_sell_trade["sl_distance"] = current_sell_trade["sl_price"] - current_sell_trade["entry_price"]
                in_sell_position = True

    # Prepare all trades DataFrame for future calculations
    all_trades = buy_trades + sell_trades
    df_all_trades = pd.DataFrame(all_trades)

    return df_all_trades

trades = backtest_trades(df=df, freq="4h", fast_ma_length=5, slow_ma_length=55, tp=8, sl=5)