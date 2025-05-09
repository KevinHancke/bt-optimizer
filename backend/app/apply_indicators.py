import pandas as pd
import pandas_ta as ta
from typing import Union

def ta_indicator(df: pd.DataFrame, indicator_name: str, params: dict, output_col: str = None) -> Union[pd.Series, pd.DataFrame]:
    """
    Applies a technical indicator to the DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame with price data.
        indicator_name (str): The name of the indicator to apply.
        params (dict): A dictionary of parameters for the indicator.
        output_col (str, optional): The name of the output column. Defaults to None.

    Returns:
        Union[pd.Series, pd.DataFrame]: The calculated indicator values.
    """
    print(f"Applying indicator: {indicator_name} with params: {params}")

    if indicator_name == 'sma':
        if 'length' not in params:
            raise ValueError("Missing 'length' parameter for SMA.")
        length = int(params['length'])
        if length <= 0:
            raise ValueError("'length' must be a positive integer.")
        col_name = output_col if output_col else f'SMA_{length}'
        result = ta.sma(df['close'], length=length)
        return result.to_frame(name=col_name)

    elif indicator_name == 'ema':
        if 'length' not in params:
            raise ValueError("Missing 'length' parameter for EMA.")
        length = int(params['length'])
        if length <= 0:
            raise ValueError("'length' must be a positive integer.")
        col_name = output_col if output_col else f'EMA_{length}'
        result = ta.ema(df['close'], length=length)
        return result.to_frame(name=col_name)

    elif indicator_name == 'rsi':
        if 'length' not in params:
            raise ValueError("Missing 'length' parameter for RSI.")
        length = int(params['length'])
        if length <= 0:
            raise ValueError("'length' must be a positive integer.")
        col_name = output_col if output_col else f'RSI_{length}'
        result = ta.rsi(df['close'], length=length)
        return result.to_frame(name=col_name)

    elif indicator_name == 'vwap':
        # Get the anchor period (D, W, M)
        anchor = params.get("anchor", "D")  # Default to Daily if not specified
        
        # Validate anchor parameter
        if anchor not in ["D", "W", "M"]:
            anchor = "D"
            
        # Calculate VWAP with the specified anchor
        try:
            col_name = output_col if output_col else f'VWAP_{anchor}'
            result = ta.vwap(high=df['high'], low=df['low'], close=df['close'], 
                            volume=df['volume'], anchor=anchor)
            return result.to_frame(name=col_name)
        except Exception as e:
            raise ValueError(f"Failed to calculate VWAP: {e}")

    elif indicator_name == 'bollinger':
        if 'length' not in params:
            raise ValueError("Missing 'length' parameter for Bollinger Bands.")
        length = int(params['length'])
        if length <= 0:
            raise ValueError("'length' must be a positive integer.")
        std_dev = float(params.get("std_dev", 2))
        result = ta.bbands(df['close'], length=length, std=std_dev)
        # Rename columns to make them identifiable
        if output_col:
            # Only rename the middle band to output_col, keep others as is
            result.columns = [f'BBL_{length}', output_col, f'BBU_{length}', f'BBB_{length}', f'BBP_{length}']
        else:
            result.columns = [f'BBL_{length}', f'BBM_{length}', f'BBU_{length}', f'BBB_{length}', f'BBP_{length}']
        return result

    elif indicator_name == 'macd':
        fast = int(params.get("fast", 12))
        slow = int(params.get("slow", 26))
        signal = int(params.get("signal", 9))
        result = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
        # Rename columns to include parameters
        if output_col:
            result.columns = [output_col, f'{output_col}_signal', f'{output_col}_hist']
        else:
            result.columns = [f'MACD_{fast}_{slow}_{signal}', f'MACDs_{fast}_{slow}_{signal}', f'MACDh_{fast}_{slow}_{signal}']
        return result

    else:
        raise ValueError(f"Unknown indicator: {indicator_name}")