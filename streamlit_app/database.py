import sqlite3
import pandas as pd
import os
import json
from datetime import datetime
import io

DB_PATH = '../data.db'

def init_db():
    """Initialize database if it doesn't exist"""
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
        CREATE TABLE price_data (
            id INTEGER PRIMARY KEY,
            ticker TEXT,
            timeframe TEXT,
            data BLOB,
            last_updated TIMESTAMP,
            UNIQUE(ticker, timeframe)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE strategies (
            id INTEGER PRIMARY KEY,
            name TEXT,
            ticker TEXT,
            timeframe TEXT,
            indicators TEXT,
            buy_conditions TEXT,
            sell_conditions TEXT,
            tp REAL,
            sl REAL,
            created_at TIMESTAMP,
            UNIQUE(name)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE backtest_results (
            id INTEGER PRIMARY KEY,
            strategy_id INTEGER,
            trades TEXT,
            performance TEXT,
            run_at TIMESTAMP,
            FOREIGN KEY (strategy_id) REFERENCES strategies(id)
        )
        ''')
        
        conn.commit()
        conn.close()

def store_price_data(ticker, timeframe, df):
    """Store price data in SQLite"""
    conn = sqlite3.connect(DB_PATH)
    
    # Convert DataFrame to binary for storage using BytesIO
    buffer = io.BytesIO()
    df.to_pickle(buffer, compression='gzip')
    df_binary = buffer.getvalue()
    
    conn.execute('''
    INSERT OR REPLACE INTO price_data (ticker, timeframe, data, last_updated)
    VALUES (?, ?, ?, ?)
    ''', (ticker, timeframe, df_binary, datetime.now()))
    
    conn.commit()
    conn.close()

def get_price_data(ticker, timeframe):
    """Retrieve price data from SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT data FROM price_data
    WHERE ticker = ? AND timeframe = ?
    ''', (ticker, timeframe))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        # Convert binary back to DataFrame using BytesIO
        buffer = io.BytesIO(result[0])
        return pd.read_pickle(buffer, compression='gzip')
    return None

def save_strategy(name, ticker, timeframe, indicators, buy_conditions, sell_conditions, tp, sl):
    """Save a strategy configuration"""
    conn = sqlite3.connect(DB_PATH)
    
    conn.execute('''
    INSERT OR REPLACE INTO strategies 
    (name, ticker, timeframe, indicators, buy_conditions, sell_conditions, tp, sl, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        name, 
        ticker, 
        timeframe, 
        json.dumps(indicators), 
        json.dumps(buy_conditions), 
        json.dumps(sell_conditions), 
        tp, 
        sl, 
        datetime.now()
    ))
    
    conn.commit()
    conn.close()

def get_all_strategies():
    """Get all saved strategies"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM strategies ORDER BY created_at DESC')
    strategies = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return strategies

def save_backtest_result(strategy_id, trades, performance):
    """Save backtest results"""
    conn = sqlite3.connect(DB_PATH)
    
    conn.execute('''
    INSERT INTO backtest_results (strategy_id, trades, performance, run_at)
    VALUES (?, ?, ?, ?)
    ''', (
        strategy_id,
        json.dumps(trades),
        json.dumps(performance),
        datetime.now()
    ))
    
    conn.commit()
    conn.close()

def store_strategy(strategy_data):
    """Store strategy in SQLite"""
    conn = sqlite3.connect(DB_PATH)
    
    conn.execute('''
    INSERT OR REPLACE INTO strategies 
    (name, ticker, timeframe, indicators, buy_conditions, sell_conditions, tp, sl, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        strategy_data['name'],
        strategy_data['ticker'],
        strategy_data['timeframe'],
        json.dumps(strategy_data['indicators']),
        json.dumps(strategy_data['buy_conditions']),
        json.dumps(strategy_data['sell_conditions']),
        strategy_data['tp'],
        strategy_data['sl'],
        datetime.now()
    ))
    
    conn.commit()
    conn.close()

def get_all_strategies():
    """Get all strategies from SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT name, ticker, timeframe, indicators, buy_conditions, sell_conditions, tp, sl, created_at
    FROM strategies
    ORDER BY created_at DESC
    ''')
    
    strategies = []
    for row in cursor.fetchall():
        strategies.append({
            'name': row[0],
            'ticker': row[1],
            'timeframe': row[2],
            'indicators': json.loads(row[3]),
            'buy_conditions': json.loads(row[4]),
            'sell_conditions': json.loads(row[5]),
            'tp': row[6],
            'sl': row[7],
            'created_at': row[8]
        })
    
    conn.close()
    return strategies

def get_strategy(name):
    """Get a specific strategy by name"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT name, ticker, timeframe, indicators, buy_conditions, sell_conditions, tp, sl, created_at
    FROM strategies
    WHERE name = ?
    ''', (name,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'name': row[0],
            'ticker': row[1],
            'timeframe': row[2],
            'indicators': json.loads(row[3]),
            'buy_conditions': json.loads(row[4]),
            'sell_conditions': json.loads(row[5]),
            'tp': row[6],
            'sl': row[7],
            'created_at': row[8]
        }
    return None

def store_backtest_result(strategy_name, result):
    """Store backtest result for a strategy"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get strategy ID
    cursor.execute('SELECT id FROM strategies WHERE name = ?', (strategy_name,))
    strategy_id = cursor.fetchone()
    
    if strategy_id:
        conn.execute('''
        INSERT INTO backtest_results (strategy_id, trades, performance, run_at)
        VALUES (?, ?, ?, ?)
        ''', (
            strategy_id[0],
            json.dumps(result.get('trades', [])),
            json.dumps(result.get('performance', {})),
            datetime.now()
        ))
    
    conn.commit()
    conn.close()
