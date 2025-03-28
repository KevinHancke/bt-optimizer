import pandas as pd
import operator
import numpy as np

def get_shifted_series(df: pd.DataFrame, operand: dict) -> pd.Series:
    column = operand.get('column')
    shift = operand.get('shift', 0)
    if column in df.columns:
        return df[column].shift(shift)
    else:
        raise ValueError(f"Column '{column}' does not exist in DataFrame.")

def apply_buy_conditions(df: pd.DataFrame, conditions: list) -> pd.DataFrame:
    if 'buy_conditions' not in df.columns:
        df['buy_conditions'] = True  # Initialize as True for logical AND

    print("Applying buy conditions with for loop")

    operators = {
        '>': operator.gt,
        '<': operator.lt,
        '==': operator.eq,
        '!=': operator.ne,
        '>=': operator.ge,
        '<=': operator.le
    }

    for condition in conditions:
        left_operand = condition['left_operand']
        comparator = condition['comparator']
        right_operand = condition['right_operand']

        print(f"Evaluating buy condition: {left_operand} {comparator} {right_operand}")

        if comparator in operators:
            left_series = get_shifted_series(df, left_operand)
            right_series = get_shifted_series(df, right_operand)
            condition_result = operators[comparator](left_series, right_series)
            condition_result = condition_result.fillna(False)  # Handle NaN values
            df['buy_conditions'] &= condition_result
            print(f"Buy conditions after applying condition: {df['buy_conditions'].value_counts().to_dict()}")
        else:
            raise ValueError(f"Invalid comparator: {comparator}")

    return df

def apply_sell_conditions(df: pd.DataFrame, conditions: list) -> pd.DataFrame:
    if 'sell_conditions' not in df.columns:
        df['sell_conditions'] = True  # Initialize as True for logical AND

    print("Applying sell conditions with for loop")

    operators = {
        '>': operator.gt,
        '<': operator.lt,
        '==': operator.eq,
        '!=': operator.ne,
        '>=': operator.ge,
        '<=': operator.le
    }

    for condition in conditions:
        left_operand = condition['left_operand']
        comparator = condition['comparator']
        right_operand = condition['right_operand']

        print(f"Evaluating sell condition: {left_operand} {operator} {right_operand}")

        if comparator in operators:
            left_series = get_shifted_series(df, left_operand)
            right_series = get_shifted_series(df, right_operand)
            condition_result = operators[comparator](left_series, right_series)
            condition_result = condition_result.fillna(False)  # Handle NaN values
            df['sell_conditions'] &= condition_result
            print(f"Sell conditions after applying condition: {df['sell_conditions'].value_counts().to_dict()}")
        else:
            raise ValueError(f"Invalid comparator: {comparator}")

    return df

def calculate_signals(df: pd.DataFrame) -> pd.DataFrame:
    print('Attempting to calculate signals')
    df['buy_signal'] = np.where(((df['buy_conditions'].shift(1) == False) & (df['buy_conditions'] == True)), 1, 0)
    df['sell_signal'] = np.where(((df['sell_conditions'].shift(1) == False) & (df['sell_conditions'] == True)), 1, 0)
    return df