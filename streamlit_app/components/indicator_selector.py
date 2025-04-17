import streamlit as st
from utils.api import apply_indicator

def indicator_selector(ticker, timeframe):
    st.subheader("2. Add Technical Indicators")
    
    if 'indicators' not in st.session_state:
        st.session_state.indicators = []
    
    # Function to add a new indicator
    def add_indicator():
        st.session_state.indicators.append({
            "type": "",
            "params": {}
        })
    
    # Function to remove an indicator
    def remove_indicator(index):
        st.session_state.indicators.pop(index)
    
    # Button to add a new indicator
    st.button("Add Indicator", on_click=add_indicator, key="add_indicator_button")
    
    # Display existing indicators and allow editing
    for i, indicator in enumerate(st.session_state.indicators):
        with st.expander(f"Indicator {i+1}: {indicator['type'] or 'Select type...'}", expanded=True):
            col1, col2, col3 = st.columns([3, 3, 1])
            
            with col1:
                indicator_type = st.selectbox(
                    "Indicator Type",
                    ["sma", "ema", "rsi", "vwap", "bollinger", "macd"],
                    index=0 if indicator["type"] == "" else ["sma", "ema", "rsi", "vwap", "bollinger", "macd"].index(indicator["type"]),
                    key=f"indicator_type_{i}"
                )
                indicator["type"] = indicator_type
            
            # Render parameter fields based on indicator type
            with col2:
                if indicator_type in ["sma", "ema"]:
                    period = st.number_input(
                        "Period", 
                        min_value=1, 
                        value=indicator.get("params", {}).get("period", 14),
                        key=f"ma_period_{i}"
                    )
                    indicator["params"] = {"period": period}
                
                elif indicator_type == "rsi":
                    period = st.number_input(
                        "Period", 
                        min_value=1, 
                        value=indicator.get("params", {}).get("period", 14),
                        key=f"rsi_period_{i}"
                    )
                    indicator["params"] = {"period": period}
                
                elif indicator_type == "bollinger":
                    period = st.number_input(
                        "Period", 
                        min_value=1, 
                        value=indicator.get("params", {}).get("period", 20),
                        key=f"bb_period_{i}"
                    )
                    stddev = st.number_input(
                        "Standard Deviation", 
                        min_value=0.1, 
                        value=indicator.get("params", {}).get("stddev", 2.0),
                        key=f"bb_stddev_{i}"
                    )
                    indicator["params"] = {"period": period, "stddev": stddev}
                
                elif indicator_type == "macd":
                    fast = st.number_input(
                        "Fast Period", 
                        min_value=1, 
                        value=indicator.get("params", {}).get("fast", 12),
                        key=f"macd_fast_{i}"
                    )
                    slow = st.number_input(
                        "Slow Period", 
                        min_value=1, 
                        value=indicator.get("params", {}).get("slow", 26),
                        key=f"macd_slow_{i}"
                    )
                    signal = st.number_input(
                        "Signal Period", 
                        min_value=1, 
                        value=indicator.get("params", {}).get("signal", 9),
                        key=f"macd_signal_{i}"
                    )
                    indicator["params"] = {"fast": fast, "slow": slow, "signal": signal}
            
            with col3:
                st.write("")
                st.write("")
                if st.button("Remove", key=f"remove_indicator_{i}"):
                    remove_indicator(i)
    
    # Button to apply indicators to chart
    if st.session_state.indicators and st.button("Apply Indicators"):
        with st.spinner("Applying indicators..."):
            result_df = apply_indicator(ticker, timeframe, st.session_state.indicators)
            if result_df is not None:
                st.session_state.data_with_indicators = result_df
                st.success("Indicators applied successfully!")
            else:
                st.error("Failed to apply indicators.")
    
    # Return the list of indicators for use in other components
    return st.session_state.indicators
