from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import traceback

from app.prepare_data import load_csv, resample_df, get_entry_price
from app.apply_indicators import ta_indicator
from app.apply_signals import apply_buy_conditions, apply_sell_conditions, calculate_signals
from app.backtest import create_empty_result, process_exit_signal, handle_buy_exit, handle_sell_exit, backtest
from app.performance_summary import calculate_performance_summary
from app.optimize import optimize

app = FastAPI()

dataframe_cache = {}

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins, 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

@app.get("/")
async def root():
    return {"message": "Backend Online interact here: http://127.0.0.1:8000/docs"}

@app.get("/api/default_chart")
async def get_default_chart(timeframe: str = '1h', ticker: str = 'BTC/USD'):
    try:
        print(f'Getting initial chart data for {ticker} with timeframe {timeframe}...')
        # Map ticker to CSV file (updated to reflect actual CSV location)
        ticker_files = {
            'BTC/USD': 'Binance_BTCUSDT_1min.csv',
            'SOL/USD': 'Binance_SOLUSDT_1min.csv',
            'JUP/USD': 'Binance_JUPUSDT_1min.csv'
        }
        if ticker not in ticker_files:
            raise Exception(f'Ticker {ticker} not found.')

        df = load_csv(ticker_files[ticker])
        df = resample_df(df, timeframe)
        df = get_entry_price(df)
        print('Data loaded and resampled successfully!')
        print(df.info())
        print(df)

        # Store the dataframe in cache
        cache_key = f"{ticker}_{timeframe}"
        dataframe_cache[cache_key] = df.copy()

        df['time'] = df.index.astype(str)
        
        return df.to_dict(orient='records')
    
    except Exception as e:
        print(f"Error loading default chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/apply_indicator")
async def apply_indicator(request: Request):
    try:
        data = await request.json()
        indicators = data.get('indicators', [])
        ticker = data.get('ticker', 'BTC/USD')
        timeframe = data.get('timeframe', '1h')
        
        print(f"Applying indicators: {indicators} for {ticker} on {timeframe} timeframe")
        
        # Use cached dataframe if available
        cache_key = f"{ticker}_{timeframe}"
        if cache_key in dataframe_cache:
            df = dataframe_cache[cache_key].copy()
            print("Using cached data")
        else:
            # Fall back to loading from CSV if not in cache
            ticker_files = {
                'BTC/USD': 'Binance_BTCUSDT_1min.csv',
                'SOL/USD': 'Binance_SOLUSDT_1min.csv',
                'JUP/USD': 'Binance_JUPUSDT_1min.csv'
            }
            if ticker not in ticker_files:
                raise Exception(f'Ticker {ticker} not found.')
                
            df = load_csv(ticker_files[ticker])
            df = resample_df(df, timeframe)
            df['time'] = df.index.astype(str)
        
        for indicator in indicators:
            # Apply indicators as before
            result = ta_indicator(df, indicator['type'], indicator.get('params', {}))
            if isinstance(result, pd.Series):
                df = df.join(result)
            elif isinstance(result, pd.DataFrame):
                df = pd.concat([df, result], axis=1)
        
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)
        print('DataFrame columns after applying indicators:', df.columns.tolist())
        print(df.info())
        print(df)
        
        # Update the cache with the dataframe including new indicators
        dataframe_cache[cache_key] = df.copy()
        
        print('Indicator applied successfully!')
        
        
        return df.to_dict(orient='records')
    
    except Exception as e:
        print(f"Error applying indicator: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/backtest")
async def run_backtest(request: Request):
    try:
        data = await request.json()
        backtest_params = data.get('backtestParams', {})
        ticker = data.get('ticker', 'BTC/USD')  
        timeframe = data.get('timeframe', '1h')
        
        # Get DataFrame from cache instead of request body
        cache_key = f"{ticker}_{timeframe}"
        if cache_key not in dataframe_cache:
            raise Exception(f'No cached data found for {ticker} on {timeframe} timeframe. Apply indicators first.')
        
        # Use the cached DataFrame with indicators already applied
        df = dataframe_cache[cache_key].copy()
        
        print(f'Using cached DataFrame with {len(df)} rows')
        print(f'Received backtest parameters: {backtest_params}')
        
        print('start backtest...')

        # Apply all buy conditions using for loops
        df = apply_buy_conditions(df, backtest_params.get('buy_conditions', []))
        print('Buy conditions applied!')

        # Apply all sell conditions using for loops
        df = apply_sell_conditions(df, backtest_params.get('sell_conditions', []))
        print('Sell conditions applied!')

        # Calculate signals after applying all conditions
        df = calculate_signals(df)
        print('Dataframe prepared!')
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        print(df.info())
        print(df)

        # Run the backtest
        trades = backtest(df, backtest_params['tp'], backtest_params['sl'])
        print(trades)

        # Calculate performance metrics
        performance = calculate_performance_summary(
            trades,
            initial_balance=10000,  # You can make this configurable
            risk_per_trade=0.01     # You can make this configurable
        )

        print('Performance summary calculated!')
        print(performance)

        result = {
            "trades": trades.to_dict(orient='records'),
            "performance": performance,
        }
        return result

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))