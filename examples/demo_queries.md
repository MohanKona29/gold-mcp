# Demo queries

Paste any of these into Claude / ChatGPT / Cursor after wiring up the
server. The model picks the right tool(s) automatically.

## Price + bars

- What is the gold price right now and how has it moved in the last 24 hours?
- Show me the last 24 hourly bars of gold. What's the trend?
- Pull the last 30 daily bars of gold and tell me the highest and lowest closes.

## Macro context

- Give me a macro snapshot for gold: DXY, US10Y, SPX, VIX, BTC, silver, oil.
- What does today's macro tape say about gold?
- Compute 60-day correlation between gold and the macro basket. Which
  cross is most negatively correlated?

## Seasonality

- Show me day-of-week seasonality for gold over 5 years. Any pattern?
- Compare monthly seasonality for gold over 10 years. Best and worst months?

## Vietnam

- USD/VND right now plus the implied world-parity gold price in VND
  per tael.
- SJC is quoting 145 million VND per tael. What's the premium vs world
  parity?

## One-call read

- Run `gold_market_snapshot` and give me the bulleted summary.
- Combine the snapshot with seasonality and tell me what's most
  notable today.
