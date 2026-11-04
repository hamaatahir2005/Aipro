import unittest
from app.quant import Candle, analyze, backtest, walk_forward, metrics
from app.trading import Risk, Rejected, validate_risk, Position, settle
from decimal import Decimal

class TradingTests(unittest.TestCase):
    def candles(self,n=210):
        return [Candle(i*60,100+i*.1,101+i*.1,99+i*.1,100.05+i*.1) for i in range(n)]
    def test_indicators(self):
        s=analyze(self.candles()); self.assertEqual(s['recommendation'],'BUY'); self.assertIsNone(s['confidence']); self.assertEqual(s['indicators']['rsi'],100)
    def test_lookahead(self):
        a=self.candles(); before=backtest(a[:150]); a[-1]=Candle(209*60,100,1000,90,999)
        self.assertEqual(before,backtest(a[:150]))
    def test_costs(self):
        a=self.candles(); self.assertGreater(backtest(a,0,0)['metrics']['net_pnl'],backtest(a,10,2)['metrics']['net_pnl'])
    def test_walkforward(self):
        for f in walk_forward(self.candles())['folds']: self.assertLess(f['train_end'],f['test_start'])
    def test_risk(self):
        validate_risk(10000,10000,10000,0,50,0,0,0,False,Risk())
        for stake,halted in [(101,False),(50,True),(-1,False)]:
            with self.assertRaises(Rejected): validate_risk(10000,10000,10000,0,stake,0,0,0,halted,Risk())
    def test_settlement(self):
        p=Position('BUY','100','1.1',0,60)
        self.assertEqual(settle(p,1.2,60),Decimal('79.900'))
        self.assertEqual(settle(p,1.0,60),Decimal('-100.100'))
        self.assertEqual(settle(p,1.1,60),Decimal('-0.100'))
        with self.assertRaises(Rejected): settle(p,1.2,59)
    def test_metrics(self):
        m=metrics([10,-5,-5,20]); self.assertEqual(m['maximum_drawdown'],10); self.assertEqual(m['consecutive_losses'],2)
    def test_bad_data(self):
        with self.assertRaises(ValueError): analyze(self.candles()[:10])
        with self.assertRaises(ValueError): Candle(0,10,9,8,10)

class ResearchTests(unittest.TestCase):
    def test_training_selection_ignores_test_suffix(self):
        from app.research import optimize
        a=TradingTests().candles(300)
        original=optimize(a)
        for i in range(211,300): a[i]=Candle(i*60,200,201,1,2)
        changed=optimize(a)
        self.assertEqual(original['selected_parameters'],changed['selected_parameters'])
        self.assertEqual(original['training_candidates'],changed['training_candidates'])
        self.assertNotEqual(original['out_of_sample'],changed['out_of_sample'])
    def test_calibration_is_historical(self):
        from app.research import calibrate
        c=calibrate(TradingTests().candles(350))
        self.assertTrue(c['ready']);self.assertLess(c['training_end'],c['validation_start'])
        self.assertGreater(c['out_of_sample_samples'],0)

class BrokerGateTests(unittest.TestCase):
    def test_real_money_disabled_by_default(self):
        import asyncio
        from app.brokers import RealExecutionGate,ExecutionAuthorization
        from app.trading import PocketOption
        with self.assertRaises(Rejected):asyncio.run(RealExecutionGate(PocketOption()).execute({},ExecutionAuthorization()))
    def test_unverified_adapter_still_rejects(self):
        import asyncio
        from app.trading import PocketOption
        with self.assertRaises(Rejected):asyncio.run(PocketOption().execute({}))
