import pandas as pd
import itertools
from typing import List, Dict, Any, Union
import concurrent.futures
from copy import deepcopy
import re
import numpy as np

from app.apply_indicators import ta_indicator
from app.apply_signals import apply_buy_conditions, apply_sell_conditions, calculate_signals
from app.backtest import backtest
from app.performance_summary import calculate_performance_summary
from app.prepare_data import resample_df, get_entry_price

def preprocess_param_ranges(param_ranges: Dict[str, Any]) -> Dict[str, List[Any]]:
    """
    Preprocess param_ranges to handle special cases like multiple instances of the same indicator.
    """
    processed_ranges = {}
    for key, values in param_ranges.items():
        # Handle multiple instances of the same indicator (e.g., SMA, VWAP, etc.)
        if isinstance(values, list) and values and isinstance(values[0], dict):
            for i, instance in enumerate(values, start=1):
                for param_key, param_values in instance.items():
                    processed_ranges[f"{key}_{i}_{param_key}"] = param_values
        # Handle single dict (legacy, e.g., vwap: {"anchor_values": [...]})
        elif isinstance(values, dict):
            for param_key, param_values in values.items():
                processed_ranges[f"{key}_{param_key}"] = param_values
        else:
            # Handle regular parameters
            processed_ranges[key] = values
    return processed_ranges

def generate_parameter_combinations(param_ranges: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """
    Generate all possible combinations of parameters.
    
    Args:
        param_ranges (dict): Dictionary mapping parameter names to lists of possible values.
            Example: {'sma_length': [5, 8, 13], 'tp': [1.01, 1.02], 'sl': [0.99, 0.98]}
    
    Returns:
        List[Dict[str, Any]]: List of parameter dictionaries, each representing one combination.
    """
    # Extract parameter names and possible values
    param_names = list(param_ranges.keys())
    param_values = list(param_ranges.values())
    
    print(f"Parameter names to be combined: {param_names}")
    
    # Generate all combinations using itertools.product
    all_combinations = list(itertools.product(*param_values))
    
    # Convert to list of dictionaries
    result = []
    for combo in all_combinations:
        param_dict = {param_names[i]: combo[i] for i in range(len(param_names))}
        result.append(param_dict)
        print(f"Generated combination: {param_dict}")
    
    return result

def run_backtest_with_params(df: pd.DataFrame, params: Dict[str, Any], buy_conditions: List[Dict], 
                            sell_conditions: List[Dict]) -> Dict[str, Any]:
   
    freq = params.get("freq_values")
    if freq:
        df_copy = resample_df(df, freq)
        df_copy = get_entry_price(df_copy)
    else:
        df_copy = df.copy()
    
    original_params = params.copy()
    print(f"Original params for this run: {original_params}")
    
    
    indicator_params = {}
    trading_params = {}
    
    for key, value in params.items():
        if '_' in key:
            parts = key.split('_')
            if len(parts) >= 2 and parts[1].isdigit():
                indicator_type = parts[0] 
                indicator_index = parts[1] 
                param_name = '_'.join(parts[2:])
                indicator_key = f"{indicator_type}_{indicator_index}"
                if indicator_key not in indicator_params:
                    indicator_params[indicator_key] = {
                        'type': indicator_type,
                        'index': indicator_index,
                        'params': {},
                        'output_col': key  # Use the param key as the output column name
                    }
                indicator_params[indicator_key]['params'][param_name] = value
            elif parts[0] in ['sma', 'ema', 'rsi', 'macd', 'vwap', 'bollinger']:
                indicator_type = parts[0]
                param_name = '_'.join(parts[1:])
                if indicator_type not in indicator_params:
                    indicator_params[indicator_type] = {
                        'type': indicator_type,
                        'params': {},
                        'output_col': key
                    }
                indicator_params[indicator_type]['params'][param_name] = value
            else:
                trading_params[key] = value
        else:
            trading_params[key] = value
    
    
    if 'tp_values' in trading_params:
        trading_params['tp'] = trading_params['tp_values']
    if 'sl_values' in trading_params:
        trading_params['sl'] = trading_params['sl_values']

    
    for ind_key, ind_config in indicator_params.items():
        ind_type = ind_config['type']
        params = ind_config['params']
        output_col = ind_config['output_col']

        # VWAP anchor_values -> anchor param fix
        if ind_type.lower() == 'vwap' and 'anchor_values' in params:
            params = params.copy()
            params['anchor'] = params.pop('anchor_values')

        result = ta_indicator(df_copy, ind_type, params, output_col=output_col)

        if isinstance(result, pd.DataFrame):
            df_copy = pd.concat([df_copy, result], axis=1)
        else:
            df_copy[output_col] = result
    
    # --- Debug prints for alignment and state ---
    print("DF index:", df_copy.index[:5])
    print("DF shape:", df_copy.shape)
    print("DF columns:", df_copy.columns.tolist())
    print("First rows:\n", df_copy.head())
    print("First entry_price values:", df_copy['entry_price'].head())
    # --- End debug prints ---

    print(f"Columns in df_copy: {df_copy.columns.tolist()}")
    print(df_copy[[col for col in df_copy.columns if 'sma' in col or 'vwap' in col]].head())

    # Create deep copies of conditions to modify for this run
    current_buy_conditions = deepcopy(buy_conditions)
    current_sell_conditions = deepcopy(sell_conditions)
    
    # Apply conditions with dynamic column names
    df_copy = apply_buy_conditions(df_copy, current_buy_conditions)
    df_copy = apply_sell_conditions(df_copy, current_sell_conditions)
    df_copy = calculate_signals(df_copy)

    # Clean up NaN and infinite values AFTER signals (matching /api/backtest)
    df_copy.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_copy.dropna(inplace=True)

    # --- Add debug print before backtest ---
    print("--- Final DF state before backtest ---")
    print("DF index:", df_copy.index[:5])
    print("DF shape:", df_copy.shape)
    print("DF columns:", df_copy.columns.tolist())
    print("First rows:\n", df_copy.head())
    print("Buy Signals Sum:", df_copy['buy_signal'].sum())
    print("Sell Signals Sum:", df_copy['sell_signal'].sum())
    # --- End debug print ---

    # Run backtest
    tp = trading_params.get('tp', 1.0)
    sl = trading_params.get('sl', 1.0)
    trades = backtest(df_copy, tp, sl)
    
    # Calculate performance
    performance = calculate_performance_summary(trades)
    
    # Return results with the original parameters used
    return {
        'params': original_params,  # Use original_params instead of potentially modified params
        'performance': performance
    }

def optimize(df: pd.DataFrame, param_ranges: Dict[str, Any], 
             buy_conditions: List[Dict], sell_conditions: List[Dict], 
             use_parallel: bool = True, max_workers: int = 4) -> pd.DataFrame:
    """
    Run optimization by testing all combinations of parameters.
    """
    # Preprocess param_ranges to handle special cases
    param_ranges = preprocess_param_ranges(param_ranges)
    
    # Generate all parameter combinations
    all_combinations = generate_parameter_combinations(param_ranges)
    print(f"Running optimization with {len(all_combinations)} parameter combinations")
    
    results = []
    
    # Use parallel or sequential processing
    if use_parallel and len(all_combinations) > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    run_backtest_with_params, 
                    df.copy(), 
                    params, 
                    buy_conditions, 
                    sell_conditions
                ) 
                for params in all_combinations
            ]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Error in worker: {e}")
    else:
        for params in all_combinations:
            try:
                result = run_backtest_with_params(df, params, buy_conditions, sell_conditions)
                results.append(result)
            except Exception as e:
                print(f"Error with params {params}: {e}")
    
    # Process results into a DataFrame
    final_results = []
    for result in results:
        if not result or 'params' not in result or 'performance' not in result:
            continue
        flat_result = {f"param_{k}": v for k, v in result['params'].items()}
        flat_result.update({f"metric_{k}": v for k, v in result['performance'].items()})
        final_results.append(flat_result)
    
    results_df = pd.DataFrame(final_results) if final_results else pd.DataFrame()
    if not results_df.empty and 'metric_profit_factor' in results_df.columns:
        results_df = results_df.sort_values(by='metric_profit_factor', ascending=False)
    
    return results_df