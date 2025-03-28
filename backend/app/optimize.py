import pandas as pd
import itertools
from typing import List, Dict, Any, Union
import concurrent.futures
from copy import deepcopy
import re

from app.apply_indicators import ta_indicator
from app.apply_signals import apply_buy_conditions, apply_sell_conditions, calculate_signals
from app.backtest import backtest
from app.performance_summary import calculate_performance_summary

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
    
    # Generate all combinations using itertools.product
    all_combinations = list(itertools.product(*param_values))
    
    # Convert to list of dictionaries
    result = []
    for combo in all_combinations:
        param_dict = {param_names[i]: combo[i] for i in range(len(param_names))}
        result.append(param_dict)
    
    return result

def run_backtest_with_params(df: pd.DataFrame, params: Dict[str, Any], buy_conditions: List[Dict], 
                            sell_conditions: List[Dict]) -> Dict[str, Any]:
    """
    Run a single backtest with specific parameters and return the results.
    
    Args:
        df (pd.DataFrame): Base DataFrame with OHLCV data
        params (Dict[str, Any]): Dictionary of parameters for this run
        buy_conditions (List[Dict]): Buy conditions template
        sell_conditions (List[Dict]): Sell conditions template
    
    Returns:
        Dict[str, Any]: Results dict with params and performance metrics
    """
    # Create a copy of the DataFrame for this run
    df_copy = df.copy()
    
    # Extract indicator params and trading params
    indicator_params = {}
    trading_params = {}
    column_mapping = {}  # Will map template column names to actual dynamic column names
    
    # Group parameters by indicator type and index (for multiple instances of same indicator)
    for key, value in params.items():
        if '_' in key:
            # Parse keys like "sma_1_length", "sma_2_length", "rsi_length"
            parts = key.split('_')
            
            # Check if it's an indexed indicator like "sma_1" or "sma_2"
            if len(parts) >= 2 and parts[1].isdigit():
                # This is an indexed indicator parameter (e.g., sma_1_length)
                indicator_type = parts[0]  # e.g., "sma"
                indicator_index = parts[1]  # e.g., "1"
                param_name = '_'.join(parts[2:])  # e.g., "length"
                
                indicator_key = f"{indicator_type}_{indicator_index}"
                if indicator_key not in indicator_params:
                    indicator_params[indicator_key] = {
                        'type': indicator_type,
                        'index': indicator_index,
                        'params': {}
                    }
                
                indicator_params[indicator_key]['params'][param_name] = value
            elif parts[0] in ['sma', 'ema', 'rsi', 'macd', 'vwap', 'bollinger']:
                # This is a non-indexed indicator parameter (e.g., rsi_length)
                indicator_type = parts[0]
                param_name = '_'.join(parts[1:])
                
                if indicator_type not in indicator_params:
                    indicator_params[indicator_type] = {
                        'type': indicator_type,
                        'params': {}
                    }
                
                indicator_params[indicator_type]['params'][param_name] = value
            else:
                # Not an indicator parameter
                trading_params[key] = value
        else:
            # Simple parameter like 'tp' or 'sl'
            trading_params[key] = value
    
    # Apply indicators with specific parameters
    for ind_key, ind_config in indicator_params.items():
        ind_type = ind_config['type']
        params = ind_config['params']
        
        # Apply the indicator
        result = ta_indicator(df_copy, ind_type, params)
        
        # Create mappings for column names based on params
        if ind_type.upper() == 'SMA' and 'length' in params:
            length = params['length']
            # For indexed SMAs (SMA_1, SMA_2), use appropriate template column name
            if 'index' in ind_config:
                template_col = f"{ind_type.upper()}_{ind_config['index']}_LENGTH"
                column_mapping[template_col] = f"{ind_type.upper()}_{length}"
            else:
                column_mapping[f"{ind_type.upper()}_LENGTH"] = f"{ind_type.upper()}_{length}"
        
        # Similar handling for other indicator types
        elif ind_type.upper() == 'RSI' and 'length' in params:
            length = params['length']
            column_mapping[f"{ind_type.upper()}_LENGTH"] = f"{ind_type.upper()}_{length}"
        elif ind_type.upper() == 'EMA' and 'length' in params:
            length = params['length']
            column_mapping[f"{ind_type.upper()}_LENGTH"] = f"{ind_type.upper()}_{length}"
        
        # Add result to DataFrame
        if isinstance(result, pd.DataFrame):
            df_copy = pd.concat([df_copy, result], axis=1)
        else:
            col_name = f"{ind_type.upper()}_{params.get('length', '')}"
            df_copy[col_name] = result
    
    # Create deep copies of conditions to modify for this run
    current_buy_conditions = deepcopy(buy_conditions)
    current_sell_conditions = deepcopy(sell_conditions)
    
    # Update column references in conditions based on parameter values
    for condition in current_buy_conditions:
        if 'left_operand' in condition and 'column' in condition['left_operand']:
            for template_col, actual_col in column_mapping.items():
                if condition['left_operand']['column'] == template_col:
                    condition['left_operand']['column'] = actual_col
                    
        if 'right_operand' in condition and 'column' in condition['right_operand']:
            for template_col, actual_col in column_mapping.items():
                if condition['right_operand']['column'] == template_col:
                    condition['right_operand']['column'] = actual_col
    
    for condition in current_sell_conditions:
        if 'left_operand' in condition and 'column' in condition['left_operand']:
            for template_col, actual_col in column_mapping.items():
                if condition['left_operand']['column'] == template_col:
                    condition['left_operand']['column'] = actual_col
                    
        if 'right_operand' in condition and 'column' in condition['right_operand']:
            for template_col, actual_col in column_mapping.items():
                if condition['right_operand']['column'] == template_col:
                    condition['right_operand']['column'] = actual_col
    
    # Apply conditions with dynamic column names
    df_copy = apply_buy_conditions(df_copy, current_buy_conditions)
    df_copy = apply_sell_conditions(df_copy, current_sell_conditions)
    df_copy = calculate_signals(df_copy)
    
    # Run backtest
    tp = trading_params.get('tp', 1.0)
    sl = trading_params.get('sl', 1.0)
    trades = backtest(df_copy, tp, sl)
    
    # Calculate performance
    performance = calculate_performance_summary(trades)
    
    # Return results with the parameters used
    return {
        'params': params,
        'performance': performance
    }

def optimize(df: pd.DataFrame, param_ranges: Dict[str, List[Any]], 
             buy_conditions: List[Dict], sell_conditions: List[Dict], 
             use_parallel: bool = True, max_workers: int = 4) -> pd.DataFrame:
    """
    Run optimization by testing all combinations of parameters.
    
    Args:
        df (pd.DataFrame): Input DataFrame with OHLCV data
        param_ranges (Dict[str, List[Any]]): Dictionary mapping parameter names to lists of values to test
        buy_conditions (List[Dict]): Buy conditions template 
        sell_conditions (List[Dict]): Sell conditions template
        use_parallel (bool): Whether to use parallel processing
        max_workers (int): Maximum number of parallel workers
    
    Returns:
        pd.DataFrame: DataFrame with all results sorted by performance
    """
    # Generate all parameter combinations
    all_combinations = generate_parameter_combinations(param_ranges)
    print(f"Running optimization with {len(all_combinations)} parameter combinations")
    
    results = []
    
    # Use parallel processing if enabled
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
        # Sequential processing
        for params in all_combinations:
            try:
                result = run_backtest_with_params(df, params, buy_conditions, sell_conditions)
                results.append(result)
            except Exception as e:
                print(f"Error with params {params}: {e}")
    
    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    
    # Create flat columns for parameters and performance metrics
    flat_results = []
    for _, row in results_df.iterrows():
        flat_row = {}
        # Add parameters
        for param_key, param_value in row['params'].items():
            flat_row[f"param_{param_key}"] = param_value
        
        # Add performance metrics
        for metric_key, metric_value in row['performance'].items():
            flat_row[f"metric_{metric_key}"] = metric_value
            
        flat_results.append(flat_row)
    
    # Convert to DataFrame and sort by profit factor (descending)
    results_flat_df = pd.DataFrame(flat_results)
    if not results_flat_df.empty:
        results_flat_df = results_flat_df.sort_values(by='metric_profit_factor', ascending=False)
    
    return results_flat_df