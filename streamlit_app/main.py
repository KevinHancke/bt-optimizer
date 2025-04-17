import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
from datetime import datetime

# Import components
from components.data_loader import data_loader
from components.indicator_selector import indicator_selector
from components.condition_builder import condition_builder
from utils.api import apply_indicator, run_backtest, run_optimization
from database import store_strategy, get_all_strategies, get_strategy, store_backtest_result

st.set_page_config(
    page_title="Backtesting Optimizer",
    page_icon="📈",
    layout="wide"
)

st.title("Backtesting Strategy Optimizer")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Build Strategy", "Saved Strategies", "Optimize Parameters"])

if page == "Build Strategy":
    # Step 1: Load data
    data_loader()
    
    if 'data_df' in st.session_state:
        # Step 2: Add indicators
        ticker = st.session_state.get('ticker_selectbox')
        timeframe = st.session_state.get('timeframe_selectbox')
        
        indicator_selector(ticker, timeframe)
        
        # Apply indicators to the data
        if st.button("Apply Indicators", key="apply_indicators_button"):
            with st.spinner("Applying indicators..."):
                if 'indicators' in st.session_state and len(st.session_state.indicators) > 0:
                    df_with_indicators = apply_indicator(
                        ticker, 
                        timeframe, 
                        st.session_state.indicators
                    )
                    if df_with_indicators is not None:
                        st.session_state.data_with_indicators = df_with_indicators
                        st.success("Indicators applied successfully!")
                    else:
                        st.error("Failed to apply indicators. Check API connection.")
                else:
                    st.session_state.data_with_indicators = st.session_state.data_df
                    st.warning("No indicators to apply. Using original data.")
        
        # Step 3: Build trading conditions
        buy_conditions, sell_conditions = condition_builder()
        
        # Step 4: Set take profit and stop loss
        st.subheader("4. Set Trade Parameters")
        col1, col2 = st.columns(2)
        with col1:
            tp = st.number_input("Take Profit (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.1, key="tp_input")
        with col2:
            sl = st.number_input("Stop Loss (%)", min_value=0.0, max_value=100.0, value=2.0, step=0.1, key="sl_input")
        
        # Step 5: Save strategy
        st.subheader("5. Save Strategy")
        strategy_name = st.text_input("Strategy Name", key="strategy_name_input")
        
        if st.button("Save Strategy", key="save_strategy_button"):
            if strategy_name:
                # Save strategy to database
                strategy_data = {
                    "name": strategy_name,
                    "ticker": ticker,
                    "timeframe": timeframe,
                    "indicators": st.session_state.indicators,
                    "buy_conditions": buy_conditions,
                    "sell_conditions": sell_conditions,
                    "tp": tp,
                    "sl": sl
                }
                
                store_strategy(strategy_data)
                st.success(f"Strategy '{strategy_name}' saved successfully!")
            else:
                st.error("Please provide a strategy name.")
        
        # Step 6: Run backtest
        st.subheader("6. Run Backtest")
        
        if st.button("Run Backtest", key="run_backtest_button"):
            with st.spinner("Running backtest..."):
                backtest_result = run_backtest(
                    ticker,
                    timeframe,
                    st.session_state.indicators,
                    buy_conditions,
                    sell_conditions,
                    tp,
                    sl
                )
                
                if backtest_result:
                    st.session_state.backtest_result = backtest_result
                    
                    # If strategy is saved, store backtest result
                    if strategy_name:
                        store_backtest_result(strategy_name, backtest_result)
                    
                    st.success("Backtest completed successfully!")
                else:
                    st.error("Backtest failed. Check API connection.")
        
        # Display backtest results
        if 'backtest_result' in st.session_state:
            st.subheader("Backtest Results")
            
            result = st.session_state.backtest_result
            
            # Display performance metrics
            metrics = result.get('performance', {})
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Return", f"{metrics.get('total_return', 0):.2f}%")
            with col2:
                st.metric("Win Rate", f"{metrics.get('win_rate', 0)::.2f}%")
            with col3:
                st.metric("Total Trades", metrics.get('total_trades', 0))
            with col4:
                st.metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
            
            # Display equity curve
            if 'equity_curve' in result:
                equity_df = pd.DataFrame(result['equity_curve'])
                st.line_chart(equity_df.set_index('timestamp')['equity'])
            
            # Display trades
            if 'trades' in result:
                trades_df = pd.DataFrame(result['trades'])
                st.dataframe(trades_df)

elif page == "Saved Strategies":
    st.subheader("Saved Strategies")
    
    # Load all strategies
    strategies = get_all_strategies()
    
    if strategies:
        strategy_names = [s["name"] for s in strategies]
        selected_strategy = st.selectbox("Select Strategy", strategy_names, key="saved_strategy_select")
        
        # Get selected strategy
        strategy = get_strategy(selected_strategy)
        
        if strategy:
            st.json(strategy)
            
            if st.button("Load Strategy", key="load_strategy_button"):
                # Load strategy into session state
                st.session_state.indicators = strategy.get('indicators', [])
                st.session_state.buy_conditions = strategy.get('buy_conditions', [])
                st.session_state.sell_conditions = strategy.get('sell_conditions', [])
                st.success(f"Strategy '{selected_strategy}' loaded successfully!")
                st.info("Go to 'Build Strategy' to edit and run this strategy.")
    else:
        st.info("No saved strategies found.")

elif page == "Optimize Parameters":
    st.subheader("Parameter Optimization")
    
    # Load all strategies
    strategies = get_all_strategies()
    
    if strategies:
        strategy_names = [s["name"] for s in strategies]
        selected_strategy = st.selectbox("Select Strategy to Optimize", strategy_names, key="optimize_strategy_select")
        
        # Get selected strategy
        strategy = get_strategy(selected_strategy)
        
        if strategy:
            st.write("Strategy details:")
            st.json(strategy)
            
            st.subheader("Parameter Ranges")
            
            # Create parameter ranges for optimization
            param_ranges = {}
            
            for i, indicator in enumerate(strategy.get('indicators', [])):
                st.write(f"Indicator: {indicator['type']}")
                
                params = indicator.get('params', {})
                for param_name, param_value in params.items():
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        min_val = st.number_input(
                            f"Min {param_name}",
                            value=float(param_value) * 0.5 if isinstance(param_value, (int, float)) else 1,
                            key=f"min_{i}_{param_name}"
                        )
                    
                    with col2:
                        max_val = st.number_input(
                            f"Max {param_name}",
                            value=float(param_value) * 1.5 if isinstance(param_value, (int, float)) else 100,
                            key=f"max_{i}_{param_name}"
                        )
                    
                    with col3:
                        step = st.number_input(
                            f"Step {param_name}",
                            value=1.0 if isinstance(param_value, (int, float)) else 1,
                            key=f"step_{i}_{param_name}"
                        )
                    
                    param_key = f"{indicator['type']}_{i}_{param_name}"
                    param_ranges[param_key] = {
                        "min": min_val,
                        "max": max_val,
                        "step": step,
                        "indicator_index": i,
                        "param_name": param_name
                    }
            
            if st.button("Run Optimization", key="run_optimization_button"):
                with st.spinner("Running optimization... This may take a while."):
                    optimization_result = run_optimization(
                        strategy['ticker'],
                        strategy['timeframe'],
                        param_ranges,
                        strategy['buy_conditions'],
                        strategy['sell_conditions']
                    )
                    
                    if optimization_result:
                        st.session_state.optimization_result = optimization_result
                        st.success("Optimization completed successfully!")
                    else:
                        st.error("Optimization failed. Check API connection.")
            
            # Display optimization results
            if 'optimization_result' in st.session_state:
                st.subheader("Optimization Results")
                
                result = st.session_state.optimization_result
                
                # Display best parameters
                st.write("Best Parameters:")
                st.json(result.get('best_params', {}))
                
                # Display best performance
                st.write("Best Performance:")
                st.json(result.get('best_performance', {}))
                
                # Display all results
                results_df = pd.DataFrame(result.get('all_results', []))
                st.dataframe(results_df)
    else:
        st.info("No saved strategies found. Create and save a strategy first.")
