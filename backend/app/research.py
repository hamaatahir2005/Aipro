"""Training-only parameter selection with a quarantined chronological test suffix."""
from math import sqrt
from .quant import ema, metrics, analyze

def strategy_returns(candles, fast, slow, start, fee_bps=10, slippage_bps=2):
    closes=[c.close for c in candles];f=ema(closes,fast);s=ema(closes,slow);returns=[]
    for i in range(max(start,slow),len(candles)):
        # Indicators stop at i-1; the execution bar i is never used in selection.
        direction=1 if f[i-1]>s[i-1] else -1
        returns.append(direction*(candles[i].close/candles[i].open-1)-2*(fee_bps+slippage_bps)/10000)
    return returns

def optimize(candles):
    if len(candles)<180: raise ValueError('180 completed bars required for optimization')
    split=int(len(candles)*.7);training=candles[:split]
    candidates=[]
    for fast,slow in [(8,21),(12,26),(20,50)]:
        result=metrics(strategy_returns(training,fast,slow,60))
        candidates.append({'fast':fast,'slow':slow,'training':result})
    winner=max(candidates,key=lambda c:c['training']['net_pnl'])
    test=metrics(strategy_returns(candles,winner['fast'],winner['slow'],split))
    return {'version':'ema-grid-v1','selected_parameters':{'fast':winner['fast'],'slow':winner['slow']},'training_candidates':candidates,'test_start_timestamp':candles[split].timestamp,'out_of_sample':test,'overfitting_warning':test['average_return']<winner['training']['average_return'],'selection_note':'Fixed 70/30 chronological split. Repeated tuning against this test invalidates its independence.'}

def calibrate(candles):
    if len(candles)<300: return {'ready':False,'reason':'At least 300 completed bars required'}
    split=int(len(candles)*.7);bins={};test=[]
    for i in range(60,len(candles)):
        signal=analyze(candles[:i]);side=signal['recommendation']
        if side=='HOLD':continue
        change=(candles[i].close/candles[i].open-1)*(1 if side=='BUY' else -1)
        success=change>0.0024
        key=str(signal['score'])
        if i<split:
            values=bins.setdefault(key,[0,0]);values[0]+=int(success);values[1]+=1
        elif key in bins and bins[key][1]>=30:
            test.append((bins[key][0]/bins[key][1],int(success)))
    estimates={}
    for key,(wins,n) in bins.items():
        if n<30:continue
        p=wins/n;z=1.96;den=1+z*z/n
        center=(p+z*z/(2*n))/den;half=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/den
        estimates[key]={'empirical_success_rate':p,'samples':n,'wilson95':[max(0,center-half),min(1,center+half)]}
    return {'ready':bool(estimates and test),'bins':estimates,'out_of_sample_samples':len(test),'brier_score':sum((p-y)**2 for p,y in test)/len(test) if test else None,'label':'Historical next-bar directional return exceeds 24bps. Not a binary payout probability or guarantee.','training_end':candles[split-1].timestamp,'validation_start':candles[split].timestamp}
