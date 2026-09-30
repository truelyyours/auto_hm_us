import argparse
from pathlib import Path

import numpy as np
import pandas as pd


RSI_PERIOD = 9
RSI_WMA_PERIOD = 21
RSI_EMA_PERIOD = 3
BB_PERIOD = 20
BB_STD_DEV = 2

HM_COLUMNS = [
    "rsi_9",
    "rsi_wma_21",
    "rsi_ema_3",
    "bb_mid_20",
    "bb_upper_20_2",
    "bb_lower_20_2",
    "hm_state",
    "hm_signal",
    "bb_position",
    "hm_bb_signal",
]


def resolve_csv_path(csv_path: str) -> Path:
    """Resolve a CSV path relative to this project root.
    Absolute paths are accepted unchanged.
    """
    path = Path(csv_path)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parent / path


def calculate_rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Calculate Wilder-style RSI from close prices.
    Returns blank values until enough rows exist.
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    average_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    average_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    relative_strength = average_gain / average_loss
    rsi = 100 - (100 / (1 + relative_strength))
    return rsi.where(average_loss != 0, 100)


def calculate_weighted_moving_average(series: pd.Series, period: int = RSI_WMA_PERIOD) -> pd.Series:
    """Calculate a weighted moving average.
    Newer values receive larger linear weights.
    """
    weights = np.arange(1, period + 1)
    return series.rolling(period).apply(lambda values: np.dot(values, weights) / weights.sum(), raw=True)


def append_indicator_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Append HM oscillator and Bollinger Band columns.
    Existing indicator columns are recalculated.
    """
    enriched = df.copy()
    close = pd.to_numeric(enriched["close"], errors="coerce")

    enriched["rsi_9"] = calculate_rsi(close)
    enriched["rsi_wma_21"] = calculate_weighted_moving_average(enriched["rsi_9"])
    enriched["rsi_ema_3"] = enriched["rsi_9"].ewm(span=RSI_EMA_PERIOD, min_periods=RSI_EMA_PERIOD, adjust=False).mean()

    enriched["bb_mid_20"] = close.rolling(BB_PERIOD).mean()
    bb_std = close.rolling(BB_PERIOD).std()
    enriched["bb_upper_20_2"] = enriched["bb_mid_20"] + (BB_STD_DEV * bb_std)
    enriched["bb_lower_20_2"] = enriched["bb_mid_20"] - (BB_STD_DEV * bb_std)

    return enriched


def identify_hm_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Append reusable HM state and signal columns.
    Requires RSI, RSI WMA, RSI EMA, and BB columns.
    """
    enriched = df.copy()
    rsi = enriched["rsi_9"]
    wma = enriched["rsi_wma_21"]
    ema = enriched["rsi_ema_3"]
    close = pd.to_numeric(enriched["close"], errors="coerce")

    bullish_state = (rsi > wma) & (rsi > ema) & (rsi > 50)
    bearish_state = (rsi < wma) & (rsi < ema) & (rsi < 50)
    bullish_cross = (rsi.shift(1) <= wma.shift(1)) & (rsi > wma)
    bearish_cross = (rsi.shift(1) >= wma.shift(1)) & (rsi < wma)
    above_bb_mid = close >= enriched["bb_mid_20"]
    below_bb_mid = close <= enriched["bb_mid_20"]

    enriched["hm_state"] = np.select(
        [bullish_state, bearish_state],
        ["BULLISH", "BEARISH"],
        default="NEUTRAL",
    )
    enriched["hm_signal"] = np.select(
        [bullish_cross, bearish_cross],
        ["BULLISH_CROSS", "BEARISH_CROSS"],
        default="",
    )
    enriched["bb_position"] = np.select(
        [above_bb_mid, below_bb_mid],
        ["ABOVE_MID", "BELOW_MID"],
        default="",
    )
    enriched["hm_bb_signal"] = np.select(
        [bullish_cross & above_bb_mid, bearish_cross & below_bb_mid],
        ["BULLISH_CONFIRMED", "BEARISH_CONFIRMED"],
        default="",
    )

    return enriched


def append_hm_data_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Append all HM and BB analysis columns.
    This is the main reusable dataframe function.
    """
    required_columns = {"close"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"CSV is missing required columns: {missing}")

    enriched = df.drop(columns=[column for column in HM_COLUMNS if column in df.columns])
    enriched = append_indicator_columns(enriched)
    return identify_hm_signals(enriched)


def update_csv_file(csv_path: Path) -> None:
    """Read one CSV, append HM columns, and overwrite it.
    The original candle columns are preserved.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    enriched = append_hm_data_columns(df)
    enriched.to_csv(csv_path, index=False)
    print(f"Updated {csv_path}")


def main() -> None:
    """Parse a single CSV path and update it in place.
    Paths are resolved relative to the project root.
    """
    parser = argparse.ArgumentParser(description="Append HM and Bollinger Band columns to one data CSV.")
    parser.add_argument("csv_path", help="CSV path relative to this project root.")
    args = parser.parse_args()

    update_csv_file(resolve_csv_path(args.csv_path))


if __name__ == "__main__":
    main()
