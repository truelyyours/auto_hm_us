import blankly
import pandas as pd
import ta
import numpy as np


# exchange = blankly.Alpaca(api_key=API_KEY, api_secret=API_SECRET, base_url=BASE_URL)

exchange = blankly.Alpaca()

def calculate_indicator(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=9).rsi()
    df['wma'] = df['rsi'].rolling(window=21).apply(lambda x: np.average(x, weights=np.arange(1, 22)), raw=True)
    df['ema'] = ta.trend.ema_indicator(df['rsi'], window=3)
    return df

def detect_signals(df):
    signals = []
    for i in range(1, len(df)):
        if df['wma'].iloc[i] > df['rsi'].iloc[i] and df['wma'].iloc[i] > df['ema'].iloc[i] and df['wma'].iloc[i-1] <= df['rsi'].iloc[i-1]:
            signals.append('BEAR')
        elif df['wma'].iloc[i] < df['rsi'].iloc[i] and df['wma'].iloc[i] < df['ema'].iloc[i] and df['wma'].iloc[i-1] >= df['rsi'].iloc[i-1]:
            signals.append('BULL')
        else:
            signals.append(None)
    return signals

def filter_stocks():
    symbols = pd.read_csv("tradable_stocks.csv")['Symbol'].tolist()
    data = []

    for symbol in symbols:
        try:
            candles = exchange.interface.history(symbol, '30m', '50')
            df = pd.DataFrame(candles)
            df = calculate_indicator(df)
            df['signal'] = detect_signals(df)

            if df['signal'].iloc[-1] is not None:
                data.append({'Stock': symbol, 'Signal': df['signal'].iloc[-1], 'Price': df['close'].iloc[-1]})

        except Exception as e:
            print(f"Error with {symbol}: {e}")

    pd.DataFrame(data).to_csv("stock_data.csv", index=False)
    print(f"Filtered {len(data)} Stocks")


