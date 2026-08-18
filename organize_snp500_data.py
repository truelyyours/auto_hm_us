import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


REQUIRED_FIELDS = {"symbol", "timeframe", "timestamp"}


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def format_date_for_name(value: str) -> str:
    return parse_timestamp(value).date().isoformat()


def safe_name(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value.upper()).strip("_")


def read_rows(input_path: Path) -> Tuple[List[str], Dict[Tuple[str, str], List[Dict[str, str]]]]:
    with input_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ValueError(f"{input_path} has no header row")

        missing_fields = REQUIRED_FIELDS.difference(reader.fieldnames)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"{input_path} is missing required columns: {missing}")

        grouped_rows: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)
        for row in reader:
            symbol = row["symbol"].strip().upper()
            timeframe = row["timeframe"].strip().upper()
            if not symbol or not timeframe or not row["timestamp"]:
                continue
            grouped_rows[(symbol, timeframe)].append(row)

    return reader.fieldnames, grouped_rows


def date_range_for_rows(rows: List[Dict[str, str]]) -> str:
    timestamps = sorted(row["timestamp"] for row in rows)
    start = format_date_for_name(timestamps[0])
    end = format_date_for_name(timestamps[-1])
    return start if start == end else f"{start}_to_{end}"


def write_grouped_data(input_path: Path, output_dir: Path) -> List[Path]:
    fieldnames, grouped_rows = read_rows(input_path)
    written_paths = []

    for (symbol, timeframe), rows in sorted(grouped_rows.items()):
        rows.sort(key=lambda row: parse_timestamp(row["timestamp"]))
        symbol_dir = output_dir / safe_name(symbol)
        symbol_dir.mkdir(parents=True, exist_ok=True)

        date_range = date_range_for_rows(rows)
        filename = f"{safe_name(symbol)}_{safe_name(timeframe)}_{date_range}.csv"
        output_path = symbol_dir / filename

        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        written_paths.append(output_path)

    return written_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Split snp500.csv into per-stock, per-timeframe CSV files.")
    parser.add_argument("--input", default="snp500.csv", help="Combined S&P 500 bars CSV.")
    parser.add_argument("--output-dir", default="data", help="Folder where symbol folders will be created.")
    args = parser.parse_args()

    written_paths = write_grouped_data(Path(args.input), Path(args.output_dir))
    print(f"Wrote {len(written_paths)} files under {args.output_dir}")


if __name__ == "__main__":
    main()
