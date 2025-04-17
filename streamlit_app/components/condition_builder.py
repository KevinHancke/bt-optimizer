import streamlit as st

def condition_builder():
    st.subheader("3. Define Trading Conditions")
    
    # Initialize session state for conditions
    if 'buy_conditions' not in st.session_state:
        st.session_state.buy_conditions = []
    if 'sell_conditions' not in st.session_state:
        st.session_state.sell_conditions = []
    
    # Get available columns for conditions
    available_columns = ["open", "high", "low", "close", "volume", "entry_price"]
    if 'data_with_indicators' in st.session_state:
        for col in st.session_state.data_with_indicators.columns:
            if col not in available_columns and col != "time":
                available_columns.append(col)
    
    # Functions to add new conditions
    def add_buy_condition():
        st.session_state.buy_conditions.append({
            "left_operand": {"column": "", "shift": 0},
            "comparator": ">",
            "right_operand": {"column": "", "shift": 0}
        })
    
    def add_sell_condition():
        st.session_state.sell_conditions.append({
            "left_operand": {"column": "", "shift": 0},
            "comparator": "<",
            "right_operand": {"column": "", "shift": 0}
        })
    
    # Functions to remove conditions
    def remove_buy_condition(index):
        st.session_state.buy_conditions.pop(index)
    
    def remove_sell_condition(index):
        st.session_state.sell_conditions.pop(index)
    
    # Tabs for buy and sell conditions
    tab1, tab2 = st.tabs(["Buy Conditions", "Sell Conditions"])
    
    with tab1:
        st.button("Add Buy Condition", on_click=add_buy_condition, key="add_buy_condition_button")
        
        for i, condition in enumerate(st.session_state.buy_conditions):
            with st.expander(f"Buy Condition {i+1}", expanded=True):
                col1, col2, col3, col4 = st.columns([3, 1, 3, 1])
                
                with col1:
                    left_col = st.selectbox(
                        "Left Column",
                        available_columns,
                        index=0 if condition["left_operand"]["column"] == "" else available_columns.index(condition["left_operand"]["column"]),
                        key=f"buy_left_col_{i}"
                    )
                    condition["left_operand"]["column"] = left_col
                    
                    left_shift = st.number_input(
                        "Left Shift",
                        min_value=0,
                        value=condition["left_operand"]["shift"],
                        key=f"buy_left_shift_{i}"
                    )
                    condition["left_operand"]["shift"] = left_shift
                
                with col2:
                    comparator = st.selectbox(
                        "Comparator",
                        [">", "<", ">=", "<=", "==", "!="],
                        index=[">", "<", ">=", "<=", "==", "!="].index(condition["comparator"]),
                        key=f"buy_comparator_{i}"
                    )
                    condition["comparator"] = comparator
                
                with col3:
                    right_col = st.selectbox(
                        "Right Column",
                        available_columns,
                        index=0 if condition["right_operand"]["column"] == "" else available_columns.index(condition["right_operand"]["column"]),
                        key=f"buy_right_col_{i}"
                    )
                    condition["right_operand"]["column"] = right_col
                    
                    right_shift = st.number_input(
                        "Right Shift",
                        min_value=0,
                        value=condition["right_operand"]["shift"],
                        key=f"buy_right_shift_{i}"
                    )
                    condition["right_operand"]["shift"] = right_shift
                
                with col4:
                    st.write("")
                    st.write("")
                    if st.button("Remove", key=f"remove_buy_{i}"):
                        remove_buy_condition(i)
    
    with tab2:
        st.button("Add Sell Condition", on_click=add_sell_condition, key="add_sell_condition_button")
        
        for i, condition in enumerate(st.session_state.sell_conditions):
            with st.expander(f"Sell Condition {i+1}", expanded=True):
                col1, col2, col3, col4 = st.columns([3, 1, 3, 1])
                
                with col1:
                    left_col = st.selectbox(
                        "Left Column",
                        available_columns,
                        index=0 if condition["left_operand"]["column"] == "" else available_columns.index(condition["left_operand"]["column"]),
                        key=f"sell_left_col_{i}"
                    )
                    condition["left_operand"]["column"] = left_col
                    
                    left_shift = st.number_input(
                        "Left Shift",
                        min_value=0,
                        value=condition["left_operand"]["shift"],
                        key=f"sell_left_shift_{i}"
                    )
                    condition["left_operand"]["shift"] = left_shift
                
                with col2:
                    comparator = st.selectbox(
                        "Comparator",
                        [">", "<", ">=", "<=", "==", "!="],
                        index=[">", "<", ">=", "<=", "==", "!="].index(condition["comparator"]),
                        key=f"sell_comparator_{i}"
                    )
                    condition["comparator"] = comparator
                
                with col3:
                    right_col = st.selectbox(
                        "Right Column",
                        available_columns,
                        index=0 if condition["right_operand"]["column"] == "" else available_columns.index(condition["right_operand"]["column"]),
                        key=f"sell_right_col_{i}"
                    )
                    condition["right_operand"]["column"] = right_col
                    
                    right_shift = st.number_input(
                        "Right Shift",
                        min_value=0,
                        value=condition["right_operand"]["shift"],
                        key=f"sell_right_shift_{i}"
                    )
                    condition["right_operand"]["shift"] = right_shift
                
                with col4:
                    st.write("")
                    st.write("")
                    if st.button("Remove", key=f"remove_sell_{i}"):
                        remove_sell_condition(i)
    
    # Return buy and sell conditions
    return st.session_state.buy_conditions, st.session_state.sell_conditions
