import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import fetch_snp500_history as history


class FetchSnp500HistoryTest(unittest.TestCase):
    def test_parse_symbols_uses_default_top_symbols_with_limit(self):
        self.assertEqual(history.parse_symbols(None, 3), ["NVDA", "AAPL", "MSFT"])

    def test_parse_symbols_accepts_comma_separated_override(self):
        self.assertEqual(history.parse_symbols("aapl, msft, nvda", 2), ["AAPL", "MSFT"])

    def test_normalize_timeframe_accepts_requested_values(self):
        self.assertEqual(history.normalize_timeframe("1D"), "1D")
        self.assertEqual(history.normalize_timeframe("1W"), "1W")
        self.assertEqual(history.normalize_timeframe("1h"), "1H")

    def test_build_bars_url_uses_alpaca_stock_bars_endpoint(self):
        url = history.build_bars_url(
            base_url="https://data.alpaca.markets",
            symbols=["AAPL", "MSFT"],
            timeframe="1D",
            start="2025-01-01",
            end=None,
            feed="iex",
            adjustment="all",
            limit=10000,
        )

        self.assertTrue(url.startswith("https://data.alpaca.markets/v2/stocks/bars?"))
        self.assertIn("symbols=AAPL%2CMSFT", url)
        self.assertIn("timeframe=1D", url)
        self.assertIn("feed=iex", url)

    @patch("fetch_snp500_history.request_json")
    def test_fetch_stock_bars_paginates_and_flattens_rows(self, request_json):
        request_json.side_effect = [
            {
                "bars": {
                    "AAPL": [
                        {"t": "2025-01-02T14:30:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 100, "n": 3, "vw": 1.4}
                    ]
                },
                "next_page_token": "next-page",
            },
            {
                "bars": {
                    "MSFT": [
                        {"t": "2025-01-02T14:30:00Z", "o": 3, "h": 4, "l": 2.5, "c": 3.5, "v": 200, "n": 4, "vw": 3.4}
                    ]
                }
            },
        ]

        rows = history.fetch_stock_bars(
            symbols=["AAPL", "MSFT"],
            timeframe="1h",
            credentials={"key": "key", "secret": "secret"},
            start="2025-01-01",
            batch_size=50,
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["symbol"], "AAPL")
        self.assertEqual(rows[0]["timeframe"], "1H")
        self.assertEqual(rows[1]["symbol"], "MSFT")
        self.assertEqual(request_json.call_count, 2)

    @patch("fetch_snp500_history.load_alpaca_credentials")
    @patch("fetch_snp500_history.fetch_stock_bars")
    def test_main_writes_combined_and_organized_csvs(self, fetch_stock_bars, load_alpaca_credentials):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_path = temp_path / "snp500.csv"
            data_dir = temp_path / "data"

            load_alpaca_credentials.return_value = {"key": "key", "secret": "secret"}
            fetch_stock_bars.return_value = [
                {
                    "symbol": "AAPL",
                    "timeframe": "1D",
                    "timestamp": "2025-07-21T04:00:00Z",
                    "open": 1,
                    "high": 2,
                    "low": 0.5,
                    "close": 1.5,
                    "volume": 100,
                    "trade_count": 3,
                    "vwap": 1.4,
                }
            ]

            argv = [
                "fetch_snp500_history.py",
                "--symbols",
                "AAPL",
                "--timeframes",
                "1D",
                "--output",
                str(output_path),
                "--data-dir",
                str(data_dir),
            ]
            with patch("sys.argv", argv):
                history.main()

            self.assertTrue(output_path.exists())
            self.assertTrue((data_dir / "AAPL" / "AAPL_1D_2025-07-21.csv").exists())


if __name__ == "__main__":
    unittest.main()
