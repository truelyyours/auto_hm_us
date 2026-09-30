# Hilega Milega Strategy Definition

I found enough to define it. Source quality is mixed: mostly TradingView scripts/descriptions and reposted setup PDFs, not a clean official spec. Also, I mostly found the creator referenced as **Nitish Kumar / Nitish Kumar Singh, NK Stock Talk**, not "Nitin Singh."

## Core HM Indicator

Hilega Milega is basically an RSI-derived oscillator system:

```text
RSI = RSI(close, 9)
WMA = WMA(RSI, 21)
EMA = EMA(RSI, 3)
Middle line = 50
```

Common line meanings:

```text
RSI(9)       = current strength / momentum
EMA(3, RSI)  = fast "price strength"
WMA(21, RSI) = slower "volume/strength" line
50 line      = bullish/bearish regime divider
```

## Canonical Signal Logic

The cleanest rule set from multiple sources is:

```text
Bullish:
RSI crosses above WMA
and preferably RSI is above EMA
and preferably RSI is above 50

Bearish:
RSI crosses below WMA
and preferably RSI is below EMA
and preferably RSI is below 50
```

A stricter version says:

```text
Buy when both WMA(21 of RSI) and EMA(3 of RSI) move below RSI.
Sell when both WMA(21 of RSI) and EMA(3 of RSI) move above RSI.
```

That maps nicely to:

```text
Bullish state: RSI > WMA and RSI > EMA
Bearish state: RSI < WMA and RSI < EMA
```

Your existing code is close to this idea, but it checks the WMA crossing relative to RSI and confirms WMA's position against EMA.

## Zones

Unlike normal RSI where `70/30` are overbought/oversold, HM commonly uses:

```text
RSI > 50 = buy/bullish zone
RSI < 50 = sell/bearish zone
```

Some notes say RSI near `70` can mean momentum is building, not necessarily overbought, and RSI can continue toward high extremes like the upper 80s. Similarly, RSI below `30` can mean downside momentum may continue.

## Multi-Timeframe Rationale

Common guidance:

```text
Higher timeframe = trend confirmation
Lower timeframe = entry/exit timing
```

Examples found:

```text
30m or 1h for trend confirmation
5m / 10m / 15m for entry and exit
```

For our fetched data, that suggests:

```text
1W = macro trend
1D = swing trend
1H = actionable signal / timing
```

## Bollinger Band Pairing

HM itself is not Bollinger Bands. BB is used as context/dynamic support-resistance:

```text
Middle BB line = SMA 20, treated as dynamic support/resistance
Upper BB = bullish target / extension zone
Lower BB = bearish target / downside extension zone
```

Common interpretation:

```text
Bullish HM + price sustaining above BB midline:
favor long continuation toward upper band

Bearish HM + price below BB midline:
favor short/weakness continuation toward lower band

RSI/WMA below 50 and price failing near BB midline:
BB midline acts like dynamic resistance

RSI/WMA above 50 and price holding BB midline:
BB midline acts like dynamic support
```

There are also references to "BB blast," where price starts riding/expanding along a band, and "BB trap/killer wave," but those are less precisely specified.

## Proposed Algorithm Definition

For our project, I'd define HM like this:

```text
Compute:
RSI_9
HM_WMA_21 = WMA(RSI_9, 21)
HM_EMA_3 = EMA(RSI_9, 3)
BB_MID = SMA(close, 20)
BB_UPPER / BB_LOWER = Bollinger Bands, 20 period, 2 std
```

Signal states:

```text
BULLISH_HM:
RSI_9 > HM_WMA_21
RSI_9 > HM_EMA_3
RSI_9 > 50

BEARISH_HM:
RSI_9 < HM_WMA_21
RSI_9 < HM_EMA_3
RSI_9 < 50
```

Trigger events:

```text
BULLISH_CROSS:
previous RSI_9 <= previous HM_WMA_21
current RSI_9 > current HM_WMA_21

BEARISH_CROSS:
previous RSI_9 >= previous HM_WMA_21
current RSI_9 < current HM_WMA_21
```

BB confirmation:

```text
BULLISH_CONFIRMED:
BULLISH_CROSS and close >= BB_MID

BEARISH_CONFIRMED:
BEARISH_CROSS and close <= BB_MID
```

## Sources

- TradingView HILEGA_MILEGA by AmarsinghShinde24: https://www.tradingview.com/script/A3VIAeLU-HILEGA-MILEGA/
- TradingView HM by NK sir: https://in.tradingview.com/script/CpsJByH2-Hilega-Milega-by-NK-sir-AM/
- Open-source Hilega-Milega by daytraderph: https://in.tradingview.com/script/GHz8LJEJ-Hilega-Milega/
- Hilega Milega setup notes: https://pdfcoffee.com/hilega-milega-setup-pdf-free.html
- MadeForTrade discussion/source snippets: https://madefortrade.in/t/hilega-milega-indicator/90094
