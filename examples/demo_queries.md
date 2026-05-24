# Demo queries

Paste any of these into Claude / ChatGPT / Cursor after wiring up the
server. The model picks the right tool(s) automatically.

## Quick reads (foundation)

- What is gold doing right now?
- Show me today's gold session: open, high, low, last, % change.
- Is the current bid/ask spread tight or wide vs. the last 24h?
- Tick activity in the last 60 seconds — quiet, normal, or news burst?

## Multi-timeframe

- Resample gold to 15m for the last 4 hours. Where does the session
  open fall in the range?
- Get 1h bars for the last 24 hours. What's the trend?

## Macro framing

- Macro snapshot for gold: DXY, US10Y, SPX, VIX, BTC, silver, oil.
  Interpret each leg.
- 60-day gold-vs-macro correlation. Which cross is the cleanest read?
- USD macro strength right now — is the gold bias bullish or bearish?

## Calendar

- High-impact macro events in the next 48 hours. Anything that
  typically moves gold?
- Next USD CPI / NFP / FOMC?

## Strategy intelligence

- Show me the Asian-box state distribution and what historically
  follows an EXPANDED Asian box.
- What are the OOS-locked parameters of the daily-setup scanner?
- What does a clean trend entry signature look like on XAUUSD?

## Vietnam

- USD/VND right now plus the implied world-parity gold price in VND.
- VN SJC tael is quoting 145M. What's the premium vs world parity?

## Compound / opinionated

- Run `analyze_gold_setup` for the 1h timeframe and give me the
  top-line read.
- Give me the morning briefing.
- I want to go long gold at 4508, stop 4495, size $10,000. Run the
  risk assessment.
- Combine: tick velocity + spread regime + macro strength + upcoming
  events. Is this a good time to scale into a position?
