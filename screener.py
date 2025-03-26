import alpaca_trade_api as tradeapi
import pandas as pd

BASE_URL = "https://api.alpaca.markets"

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL)

def get_tradable_stocks():
    assets = api.list_assets()
    tradable_stocks = [a.symbol for a in assets if a.tradable and a.easy_to_borrow]
    return tradable_stocks

def fetch_market_cap(symbol):
    try:
        snapshot = api.get_snapshot(symbol)
        market_cap = snapshot.fundamental.market_cap
        return market_cap
    except:
        return None

def filter_stocks():
    tradable = get_tradable_stocks()
    stocks = []
    for symbol in tradable:
        cap = fetch_market_cap(symbol)
        if cap and (2e9 <= cap <= 10e9 or cap > 10e9):
            stocks.append(symbol)

    pd.DataFrame(stocks, columns=['Symbol']).to_csv("tradable_stocks.csv", index=False)
    print(f"{len(stocks)} Midcap/Largecap Stocks Saved")

if __name__ == "__main__":
    filter_stocks()

