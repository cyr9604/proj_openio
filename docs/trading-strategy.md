# 520 Moving Average Trading Strategy

The 520 strategy uses the 5-period MA (MA5) and 20-period MA (MA20) as core indicators for entry and exit decisions — no other lines needed.

## Core Logic

- **MA5 (5-period)**: Average closing price over the last 5 days. Sensitive, reflects short-term sentiment.
- **MA20 (20-period)**: Average closing price over the last 20 days. The "lifeline" — stable, filters noise, defines medium-term trend.

**Key rule**: Short-term follows medium-term. Golden crosses are only valid when MA20 is rising. When MA20 is falling, ignore all signals.

## Step 1: Determine the Trend (MA20 is the Prerequisite)

Check MA20 first. Only three scenarios:

1. **MA20 rising** → Medium-term bullish, actionable. Look for buy signals.
2. **MA20 flat** → Range-bound, wait. No buying or selling to avoid whipsaws.
3. **MA20 falling** → Medium-term bearish. Do NOT enter. Trading against the trend is a losing game.

> Key: Don't try to catch falling knives. When MA20 is falling, all bounces are temporary. Stay disciplined to avoid 80% of deep drawdowns.

## Step 2: Find Buy Signals (Three Valid Setups)

Only buy when MA20 is rising AND one of these three patterns appears:

### 1. Golden Cross Entry

**Conditions**:
- MA20 clearly rising
- MA5 crosses above MA20 (golden cross), both sloping upward
- Volume at least 1.5x the average on golden cross day
- Price holds firmly above the moving averages

**Logic**: A volume-backed golden cross signals real money flowing in, not a false signal.

**Position**: 30% initial position. No full allocation.

### 2. Pullback Entry (Second Entry, Higher Win Rate)

**Conditions**:
- Price rallied after golden cross, then pulls back toward MA20
- Pullback does not effectively break MA20 (recovers same day or next)
- Volume contracts 50%-70% during the pullback
- A volume-backed bullish candle reclaims MA5 after the contraction

**Logic**: A shrinking-volume pullback is institutional shakeout, not distribution. Trend remains up.

**Position**: Add another 20% after confirmation. Never full position.

### 3. MA Convergence / Divergence Entry (Momentum Setup)

**Conditions**:
- MA5 and MA20 converge (narrow spread) for 5+ sessions
- Sudden volume spike, MA5 crosses above MA20, both diverge rapidly upward
- Price breaks above the previous range

**Logic**: Convergence is accumulation; divergence is the start of a markup phase.

**Position**: 40%, fast in and out. Don't get greedy.

## Step 3: Exit and Stop-Loss Rules

### Stop-Loss

1. **Short-term stop**: Close breaks below MA5, not recovered next day → exit immediately. Max loss capped at 5%.
2. **Trend stop**: Close breaks below MA20 with volume, not recovered by close → unconditional liquidation. Medium-term trend is broken.

> Never average down. Small accounts cannot afford averaging. Cut losses and wait for the next signal.

### Take-Profit

1. **Normal**: 3%-5% profit → sell. Small accounts grow through accumulated gains.
2. **Strong trend**: Consecutive volume-backed up days, both MAs diverging → hold until MA5 crosses below MA20 (death cross), then liquidate.

**Core principle**: Profit in hand is your profit. Don't let winners turn into losers.

## Position Sizing

| Scenario | Position | Rationale |
|----------|----------|-----------|
| Initial entry | 30% | Probing the trade |
| Add after pullback | Up to 50% (hard limit) | Confirmation |
| Cash reserve | Always 50%+ | Buffer for unexpected events |

## Common Mistakes

1. **Buying golden crosses without checking MA20 trend** → All golden crosses with a falling MA20 are traps. Ignore them.
2. **Entering on low-volume golden crosses** → Without volume confirmation, it's a false signal.
3. **Selling into a volume-backed pullback** → Volume on the pullback means distribution, not shakeout.
4. **Overtrading in range-bound markets** → When MA20 is flat, signals are unreliable.
5. **No stop-loss** → Small losses turn into catastrophic drawdowns.
6. **Greed on winners** → Letting profits evaporate by not taking gains.

> Small accounts succeed by executing a simple strategy with discipline — no emotions, no random trades. Build capital steadily.
