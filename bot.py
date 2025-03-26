from blankly import Screener, Alpaca, ScreenerState


def evaluator(symbol, state: ScreenerState):
    pass


def formatter(results, state: ScreenerState):
    pass


if __name__ == '__main__':
    exchange = Alpaca()  # initialize our exchange
    screener = Screener(exchange, evaluator, symbols=[], formatter=formatter)  # find oversold

    print(screener.formatted_results)
