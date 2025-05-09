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

        # Always load raw data for backtest, not from cache
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

        # Apply indicators as in optimization
        indicators = backtest_params.get('indicators', [])
        for indicator in indicators:
            result = ta_indicator(df, indicator['type'], indicator.get('params', {}))
            if isinstance(result, pd.Series):
                df = df.join(result)
            elif isinstance(result, pd.DataFrame):
                df = pd.concat([df, result], axis=1)
        
        # Clean up NaN and infinite values before backtest
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        # --- Debug prints for alignment and state ---
        print("DF index:", df.index[:5])
        print("DF shape:", df.shape)
        print("DF columns:", df.columns.tolist())
        print("First rows:\n", df.head())
        print("First entry_price values:", df['entry_price'].head())
        # --- End debug prints ---

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

        # --- Add debug print before backtest ---
        print("--- Final DF state before backtest ---")
        print("DF index:", df.index[:5])
        print("DF shape:", df.shape)
        print("DF columns:", df.columns.tolist())
        print("First rows:\n", df.head())
        print("Buy Signals Sum:", df['buy_signal'].sum())
        print("Sell Signals Sum:", df['sell_signal'].sum())
        # --- End debug print ---

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

@app.post("/api/optimize")
async def run_optimization(request: Request):
    try:
        data = await request.json()
        ticker = data.get('ticker', 'BTC/USD')
        timeframe = data.get('timeframe', '1h')
        param_ranges = data.get('param_ranges', {})
        buy_conditions = data.get('buy_conditions', [])
        sell_conditions = data.get('sell_conditions', [])
        use_parallel = data.get('use_parallel', True)
        max_workers = data.get('max_workers', 4)
        
        print(f"Starting optimization for {ticker} on {timeframe} timeframe")
        # ...existing debug prints...

        # Always load the raw data for optimization (do not use cached DataFrame with indicators)
        ticker_files = {
            'BTC/USD': 'Binance_BTCUSDT_1min.csv',
            'SOL/USD': 'Binance_SOLUSDT_1min.csv',
            'JUP/USD': 'Binance_JUPUSDT_1min.csv'
        }
        if ticker not in ticker_files:
            raise Exception(f'Ticker {ticker} not found.')
        df = load_csv(ticker_files[ticker])
        # Do not resample here; let optimize/resample_df handle it per parameter set

        print(f"Running optimization with {len(df)} data points")
        
        # Run optimization
        results_df = optimize(
            df=df,
            param_ranges=param_ranges,
            buy_conditions=buy_conditions,
            sell_conditions=sell_conditions,
            use_parallel=use_parallel,
            max_workers=max_workers
        )

        # Convert results to dict for JSON response
        results = results_df.to_dict(orient='records')
        
        # Check if results contain the expected parameters
        if results:
            print("Full results data structure:")
            for col in results_df.columns:
                print(f"Column: {col}")
                
            # Let's inspect the first result more carefully
            first_result = results[0]
            print(f"First result keys: {first_result.keys()}")
            
            # Check if we have any columns with sma_1_length or sma_2_length
            sma_columns = [col for col in results_df.columns if 'sma' in col.lower()]
            print(f"SMA-related columns: {sma_columns}")
            
        # Debug the optimization results
        if not results_df.empty:
            print(f"Columns in results_df: {results_df.columns.tolist()}")
            print(f"First row: {results_df.iloc[0].to_dict()}")
        
        # Convert results to dict for JSON response
        results = results_df.to_dict(orient='records')
        
        print(f"Optimization complete. Found {len(results)} results.")
        
        # Extract information about the best combination
        best_params = {}
        best_combination = ""
        if results:
            best_params = {k.replace('param_', ''): v for k, v in results[0].items() 
                          if k.startswith('param_') and k != 'param_combination'}
            best_combination = results[0].get('param_combination', '')
            
        return {
            "results": results,
            "best_params": best_params,
            "best_combination": best_combination,
            "total_combinations": len(results)
        }
        
    except Exception as e:
        print(f"Error during optimization: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))