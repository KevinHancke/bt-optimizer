import requests
import pandas as pd
import json

API_BASE_URL = "http://127.0.0.1:8000/api"

def get_default_chart(ticker, timeframe):
    """Get chart data from API"""
    response = requests.get(f"{API_BASE_URL}/default_chart?ticker={ticker}&timeframe={timeframe}")
    if response.status_code == 200:
        return pd.DataFrame(response.json())
    return None

def apply_indicator(ticker, timeframe, indicators):
    """Apply indicators to chart"""
    payload = {
        "ticker": ticker,
        "timeframe": timeframe,
        "indicators": indicators
    }
    response = requests.get(
        f"{API_BASE_URL}/apply_indicator", 
        json=payload
    )
    if response.status_code == 200:
        return pd.DataFrame(response.json())
    return None

def run_backtest(ticker, timeframe, indicators, buy_conditions, sell_conditions, tp, sl):
    """Run backtest"""
    payload = {
        "ticker": ticker,
        "timeframe": timeframe,
        "backtestParams": {
            "indicators": indicators,
            "buy_conditions": buy_conditions,
            "sell_conditions": sell_conditions,
            "tp": tp,
            "sl": sl
        }
    }
    response = requests.post(
        f"{API_BASE_URL}/backtest", 
        json=payload
    )
    if response.status_code == 200:
        return response.json()
    return None

def run_optimization(ticker, timeframe, param_ranges, buy_conditions, sell_conditions):
    """Run optimization"""
    payload = {
        "ticker": ticker,
        "timeframe": timeframe,
        "param_ranges": param_ranges,
        "buy_conditions": buy_conditions,
        "sell_conditions": sell_conditions,
        "use_parallel": True,
        "max_workers": 4
    }
    response = requests.post(
        f"{API_BASE_URL}/optimize", 
        json=payload
    )
    if response.status_code == 200:
        return response.json()
    return None
