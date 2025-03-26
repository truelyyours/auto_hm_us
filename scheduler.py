import schedule
import time
import screener
from main import filter_stocks

def run_all():
    screener.filter_stocks()
    filter_stocks()

schedule.every().day.at("07:00").do(screener.filter_stocks)
schedule.every(15).minutes.do(filter_stocks)

while True:
    schedule.run_pending()
    time.sleep(1)

