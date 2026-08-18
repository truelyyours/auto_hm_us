import csv
import tempfile
import unittest
from pathlib import Path

import organize_snp500_data as organizer


class OrganizeSnp500DataTest(unittest.TestCase):
    def test_write_grouped_data_creates_symbol_timeframe_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "snp500.csv"
            output_dir = temp_path / "data"

            with input_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
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
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "symbol": "AAPL",
                            "timeframe": "1D",
                            "timestamp": "2025-07-22T04:00:00Z",
                            "open": "1",
                            "high": "2",
                            "low": "0.5",
                            "close": "1.5",
                            "volume": "100",
                            "trade_count": "3",
                            "vwap": "1.4",
                        },
                        {
                            "symbol": "AAPL",
                            "timeframe": "1D",
                            "timestamp": "2025-07-21T04:00:00Z",
                            "open": "1",
                            "high": "2",
                            "low": "0.5",
                            "close": "1.5",
                            "volume": "100",
                            "trade_count": "3",
                            "vwap": "1.4",
                        },
                        {
                            "symbol": "MSFT",
                            "timeframe": "1H",
                            "timestamp": "2025-07-21T14:00:00Z",
                            "open": "3",
                            "high": "4",
                            "low": "2.5",
                            "close": "3.5",
                            "volume": "200",
                            "trade_count": "4",
                            "vwap": "3.4",
                        },
                    ]
                )

            written_paths = organizer.write_grouped_data(input_path, output_dir)

            self.assertEqual(len(written_paths), 2)
            self.assertTrue((output_dir / "AAPL" / "AAPL_1D_2025-07-21_to_2025-07-22.csv").exists())
            self.assertTrue((output_dir / "MSFT" / "MSFT_1H_2025-07-21.csv").exists())


if __name__ == "__main__":
    unittest.main()
