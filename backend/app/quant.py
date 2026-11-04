"""Causal indicators and chronological research; no external numerical dependencies."""
from dataclasses import dataclass
from math import sqrt
from statistics import mean, pstdev

@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0
    def __post_init__(self):
        if min(self.open, self.low, self.close) <= 0 or self.high < max(self.open, self.close, self.low) or self.low > min(self.open, self.close):
            raise ValueError('Invalid OHLC')

def ema(values, period):
    if not values or period < 1: raise ValueError('Invalid EMA input')
    result = [values[0]]
    for value in values[1:]: result.append(result[-1] + 2 / (period + 1) * (value - result[-1]))
    return result

def analyze(candles, symbol='EUR/USD', timeframe='1min'):
    if len(candles) < 60: raise ValueError('At least 60 completed candles required')
    if any(a.timestamp >= b.timestamp for a,b in zip(candles,candles[1:])): raise ValueError('Candles must be strictly chronological')
    close = [c.close for c in candles]
    changes = [b-a for a,b in zip(close,close[1:])][-14:]
    gain, loss = mean([max(x,0) for x in changes]), mean([max(-x,0) for x in changes])
    rsi = 100 - 100/(1+gain/loss) if loss else (100 if gain else 50)
    fast, slow = ema(close,12), ema(close,26)
    macds = [a-b for a,b in zip(fast,slow)]
    tr = [max(b.high-b.low,abs(b.high-a.close),abs(b.low-a.close)) for a,b in zip(candles,candles[1:])]
    atr = mean(tr[-14:])
    plus,minus = [],[]
    for a,b in zip(candles,candles[1:]):
        up,down=b.high-a.high,a.low-b.low
        plus.append(up if up>down and up>0 else 0)
        minus.append(down if down>up and down>0 else 0)
    dx=[]
    for i in range(14,len(tr)+1):
        p,m=sum(plus[i-14:i]),sum(minus[i-14:i])
        dx.append(100*abs(p-m)/(p+m) if p+m else 0)
    e20,e50=ema(close,20)[-1],ema(close,50)[-1]
    mid,sd=mean(close[-20:]),pstdev(close[-20:])
    c,p=candles[-1],candles[-2]
    patterns=[]
    if abs(c.close-c.open)<=0.1*(c.high-c.low): patterns.append('doji')
    if c.close>c.open and p.close<p.open and c.open<=p.close and c.close>=p.open: patterns.append('bullish_engulfing')
    if c.close<c.open and p.close>p.open and c.open>=p.close and c.close<=p.open: patterns.append('bearish_engulfing')
    score=(1 if e20>e50 else -1)+(1 if macds[-1]>ema(macds,9)[-1] else -1)+(1 if 50<rsi<70 else -1 if 30<rsi<50 else 0)
    return {'symbol':symbol,'timeframe':timeframe,'timestamp':c.timestamp,'recommendation':'BUY' if score>=2 else 'SELL' if score<=-2 else 'HOLD','score':score,'confidence':None,'confidence_note':'Uncalibrated; score is not a probability','risk':'high' if atr/c.close>.02 else 'moderate','holding_period_seconds':300,'indicators':{'rsi':rsi,'macd':macds[-1],'macd_signal':ema(macds,9)[-1],'ema20':e20,'ema50':e50,'sma20':mid,'bollinger_upper':mid+2*sd,'bollinger_lower':mid-2*sd,'atr':atr,'adx':mean(dx[-14:]),'support':min(x.low for x in candles[-20:]),'resistance':max(x.high for x in candles[-20:]),'trend':'up' if e20>e50 else 'down','momentum':close[-1]/close[-11]-1,'volatility':sd/mid,'patterns':patterns}}

def metrics(returns):
    equity=peak=drawdown=0.; streak=worst=0
    for value in returns:
        equity+=value; peak=max(peak,equity); drawdown=max(drawdown,peak-equity)
        streak=streak+1 if value<0 else 0; worst=max(worst,streak)
    wins=sum(x for x in returns if x>0); losses=-sum(x for x in returns if x<0)
    return {'trades':len(returns),'net_pnl':sum(returns),'win_rate':sum(x>0 for x in returns)/len(returns) if returns else 0,'maximum_drawdown':drawdown,'profit_factor':wins/losses if losses else None,'average_return':mean(returns) if returns else 0,'expected_value':mean(returns) if returns else 0,'consecutive_losses':worst,'risk_adjusted':mean(returns)/pstdev(returns)*sqrt(len(returns)) if len(returns)>1 and pstdev(returns)>0 else None}

def backtest(candles, fee_bps=10, slippage_bps=2, start=60):
    """Signals from completed bar i; fill at next open, exit at next close."""
    pnl=[]
    for i in range(max(60,start),len(candles)):
        signal=analyze(candles[:i])['recommendation']
        if signal=='HOLD': continue
        c=candles[i]; direction=1 if signal=='BUY' else -1
        pnl.append(direction*(c.close/c.open-1)-(fee_bps+slippage_bps)*2/10000)
    return {'strategy_version':'ema-momentum-v1','metrics':metrics(pnl),'returns':pnl}

def walk_forward(candles, train=120, test=30):
    if train<60 or test<1: raise ValueError('Invalid windows')
    folds=[]
    for boundary in range(train,len(candles)-test+1,test):
        candidates=[(cost,backtest(candles[:boundary],fee_bps=cost)['metrics']['net_pnl']) for cost in (5,10,20)]
        # Costs are stress scenarios, never optimized into a favorable execution assumption.
        result=backtest(candles[:boundary+test],start=boundary)
        folds.append({'train_end':candles[boundary-1].timestamp,'test_start':candles[boundary].timestamp,'cost_stress':candidates,'out_of_sample':result})
    return {'folds':folds,'warning':'Small samples and repeated research can overfit. No probability calibration inferred.'}
