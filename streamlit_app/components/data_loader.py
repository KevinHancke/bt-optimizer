import streamlit as st
import pandas as pd
from utils.api import get_default_chart
from database import store_price_data, get_price_data, init_db

def data_loader():
    st.subheader("1. Load Market Data")
    
    # Initialize database if needed
    init_db()
    
    col1, col2 = st.columns(2)
    
    with col1:
        ticker = st.selectbox(
            "Select Ticker",
            ["BTC/USD", "SOL/USD", "JUP/USD"],
            key="ticker_selectbox"
        )
    
    with col2:
        timeframe = st.selectbox(
            "Select Timeframe",
            ["1m", "5m", "15m", "1h", "4h", "1d"],
            index=3,  # Default to 1h
            key="timeframe_selectbox"
        )
    
    # Check if we have the data in database first
    df = get_price_data(ticker, timeframe)
    if df is None:
        if st.button("Load Data"):
            with st.spinner(f"Loading {ticker} data for {timeframe} timeframe..."):
                df = get_default_chart(ticker, timeframe)
                if df is not None:
                    store_price_data(ticker, timeframe, df)
                    st.session_state.data_df = df
                    st.success(f"Successfully loaded {ticker} data for {timeframe} timeframe!")
                else:
                    st.error("Failed to load data. Check if backend is running.")
    else:
        st.session_state.data_df = df
        st.success(f"Using cached {ticker} data for {timeframe} timeframe")
    
    # If we have data, show a preview
    if 'data_df' in st.session_state and st.session_state.data_df is not None:
        st.write("Data Preview:")
        st.dataframe(st.session_state.data_df.head())
        
        # Return selected ticker and timeframe for other components
        return ticker, timeframe
    
    return None, None
