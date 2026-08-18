import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from organize_snp500_data import write_grouped_data


DATA_BASE_URL = "https://data.alpaca.markets"
STOCK_BARS_PATH = "/v2/stocks/bars"

# Current top SPY / S&P 500 holdings by weight, used as a deliberately capped
# default universe while this project is still in data-validation mode.
DEFAULT_TOP_SP500_SYMBOLS = [
    "NVDA",
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "AVGO",
    "GOOG",
    "META",
    "TSLA",
    "MU",
]

TIMEFRAME_ALIASES = {
    "1D": "1D",
    "1DAY": "1D",
    "1W": "1W",
    "1WEEK": "1W",
    "1H": "1H",
    "1HR": "1H",
    "1HOUR": "1H",
}

CSV_FIELDS = [
    "symbol",
    "timeframe",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trade_count",
    "vwap",
]


def normalize_timeframe(timeframe: str) -> str:
    normalized = timeframe.strip().upper()
    if normalized not in TIMEFRAME_ALIASES:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return TIMEFRAME_ALIASES[normalized]


def parse_symbols(symbols: Optional[str], limit: int) -> List[str]:
    if symbols:
        parsed = [symbol.strip().upper() for symbol in symbols.split(",")]
        parsed = [symbol for symbol in parsed if symbol]
    else:
        parsed = DEFAULT_TOP_SP500_SYMBOLS.copy()

    if limit < 1:
        raise ValueError("--limit must be at least 1")
    return parsed[:limit]


def load_alpaca_credentials(keys_path: Path, portfolio: Optional[str] = None) -> Dict[str, str]:
    with keys_path.open("r", encoding="utf-8") as file:
        keys = json.load(file)

    alpaca_keys = keys.get("alpaca", {})
    if not alpaca_keys:
        raise ValueError(f"No alpaca credentials found in {keys_path}")

    if portfolio:
        account = alpaca_keys.get(portfolio)
        if account is None:
            raise ValueError(f"No alpaca portfolio named {portfolio!r} in {keys_path}")
    else:
        account = next(iter(alpaca_keys.values()))

    api_key = account.get("API_KEY") or account.get("APCA_API_KEY_ID")
    api_secret = account.get("API_SECRET") or account.get("APCA_API_SECRET_KEY")
    if not api_key or not api_secret:
        raise ValueError(f"Alpaca API key/secret missing in {keys_path}")

    return {"key": api_key, "secret": api_secret}


def chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def request_json(url: str, credentials: Dict[str, str]) -> Dict:
    request = Request(
        url,
        headers={
            "APCA-API-KEY-ID": credentials["key"],
            "APCA-API-SECRET-KEY": credentials["secret"],
            "accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Alpaca API returned HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach Alpaca API: {error.reason}") from error


def build_bars_url(
    base_url: str,
    symbols: List[str],
    timeframe: str,
    start: str,
    end: Optional[str],
    feed: str,
    adjustment: str,
    limit: int,
    page_token: Optional[str] = None,
) -> str:
    params = {
        "symbols": ",".join(symbols),
        "timeframe": timeframe,
        "start": start,
        "feed": feed,
        "adjustment": adjustment,
        "limit": str(limit),
    }
    if end:
        params["end"] = end
    if page_token:
        params["page_token"] = page_token

    return f"{base_url.rstrip('/')}{STOCK_BARS_PATH}?{urlencode(params)}"


def fetch_stock_bars(
    symbols: List[str],
    timeframe: str,
    credentials: Dict[str, str],
    start: str,
    end: Optional[str] = None,
    base_url: str = DATA_BASE_URL,
    feed: str = "iex",
    adjustment: str = "all",
    request_limit: int = 10000,
    batch_size: int = 50,
) -> List[Dict]:
    rows = []
    timeframe = normalize_timeframe(timeframe)

    for symbol_batch in chunked(symbols, batch_size):
        page_token = None
        while True:
            url = build_bars_url(
                base_url=base_url,
                symbols=symbol_batch,
                timeframe=timeframe,
                start=start,
                end=end,
                feed=feed,
                adjustment=adjustment,
                limit=request_limit,
                page_token=page_token,
            )
            payload = request_json(url, credentials)
            bars_by_symbol = payload.get("bars", {})

            for symbol, bars in bars_by_symbol.items():
                for bar in bars:
                    rows.append(
                        {
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "timestamp": bar.get("t"),
                            "open": bar.get("o"),
                            "high": bar.get("h"),
                            "low": bar.get("l"),
                            "close": bar.get("c"),
                            "volume": bar.get("v"),
                            "trade_count": bar.get("n"),
                            "vwap": bar.get("vw"),
                        }
                    )

            page_token = payload.get("next_page_token")
            if not page_token:
                break

    return rows


def write_csv(rows: List[Dict], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def default_start_date(lookback_days: int) -> str:
    start = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    return start.date().isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch top S&P 500 historical bars from Alpaca.")
    parser.add_argument("--keys", default="keys.json", help="Path to Blankly-style keys.json.")
    parser.add_argument("--portfolio", default="paper-api", help="Alpaca portfolio name inside keys.json.")
    parser.add_argument("--output", default="snp500.csv", help="CSV output path.")
    parser.add_argument("--data-dir", default="data", help="Folder where per-symbol CSV files will be created.")
    parser.add_argument("--symbols", default=None, help="Comma-separated symbols. Defaults to top S&P names.")
    parser.add_argument("--limit", type=int, default=len(DEFAULT_TOP_SP500_SYMBOLS), help="Max symbols to fetch.")
    parser.add_argument("--timeframes", nargs="+", default=["1D", "1W", "1h"], help="Timeframes to fetch.")
    parser.add_argument("--lookback-days", type=int, default=365, help="Historical lookback if --start is omitted.")
    parser.add_argument("--start", default=None, help="Inclusive start date/time, e.g. 2025-01-01.")
    parser.add_argument("--end", default=None, help="Inclusive end date/time. Defaults to Alpaca's latest available.")
    parser.add_argument("--feed", default="iex", help="Market data feed, e.g. iex, sip, delayed_sip.")
    parser.add_argument("--adjustment", default="all", help="Adjustment mode, e.g. raw, split, dividend, all.")
    parser.add_argument("--batch-size", type=int, default=50, help="Symbols per API request.")
    args = parser.parse_args()

    symbols = parse_symbols(args.symbols, args.limit)
    timeframes = [normalize_timeframe(timeframe) for timeframe in args.timeframes]
    start = args.start or default_start_date(args.lookback_days)
    credentials = load_alpaca_credentials(Path(args.keys), args.portfolio)

    rows = []
    try:
        for timeframe in timeframes:
            timeframe_rows = fetch_stock_bars(
                symbols=symbols,
                timeframe=timeframe,
                credentials=credentials,
                start=start,
                end=args.end,
                feed=args.feed,
                adjustment=args.adjustment,
                batch_size=args.batch_size,
            )
            rows.extend(timeframe_rows)
            print(f"Fetched {len(timeframe_rows)} {timeframe} bars")
    except RuntimeError as error:
        print(error, file=sys.stderr)
        sys.exit(1)

    rows.sort(key=lambda row: (row["symbol"], row["timeframe"], row["timestamp"] or ""))
    output_path = Path(args.output)
    write_csv(rows, output_path)
    print(f"Saved {len(rows)} rows for {len(symbols)} symbols to {args.output}")

    written_paths = write_grouped_data(output_path, Path(args.data_dir))
    print(f"Wrote {len(written_paths)} organized files under {args.data_dir}")


if __name__ == "__main__":
    main()
