import pandas as pd
import operator
import numpy as np

def load_csv(filepath: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(filepath)
        df = df.iloc[:, :6]
        df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
        df.reset_index(drop=True, inplace=True)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        return df
    except ValueError as ve:
        raise ValueError(f"Error loading CSV file: {ve}")
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found at path: {filepath}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred while loading CSV: {e}")

def resample_df(df: pd.DataFrame, freq: str) -> pd.DataFrame:   
    try:
        resampled_open = df.open.resample(freq).first()
        resampled_high = df.high.resample(freq).max()
        resampled_low = df.low.resample(freq).min()
        resampled_close = df.close.resample(freq).last()
        resampled_volume = df.volume.resample(freq).sum()
        df = pd.concat([resampled_open, resampled_high, resampled_low, resampled_close, resampled_volume], axis=1)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        raise Exception(f"Error resampling DataFrame: {e}")

def get_entry_price(df: pd.DataFrame) -> pd.DataFrame:
    df['entry_price'] = df['open'].shift(-1)
    return df.iloc[:-1]