from dataclasses import dataclass, asdict
from decimal import Decimal

@dataclass
class Risk:
    per_trade: float = .01
    daily_loss: float = .03
    drawdown: float = .10
    max_positions: int = 1
    max_losses: int = 3
    daily_trades: int = 10

class Rejected(ValueError): pass

def validate_risk(balance, initial, peak, day_pnl, stake, positions, losses, count, halted, risk):
    if halted: raise Rejected('Emergency stop active')
    if balance<=0 or initial<=0 or peak<=0: raise Rejected('Invalid account equity')
    if not 0<stake<=balance*risk.per_trade: raise Rejected('Per-trade risk exceeded')
    if day_pnl-stake < -initial*risk.daily_loss: raise Rejected('Daily loss budget exhausted')
    if (peak-balance+stake)/peak>risk.drawdown: raise Rejected('Drawdown limit')
    if positions>=risk.max_positions or losses>=risk.max_losses or count>=risk.daily_trades: raise Rejected('Trading limit reached')

@dataclass
class Position:
    side: str
    stake: str
    entry: str
    opened_at: int
    expires_at: int
    payout: str = '0.8'
    fee: str = '0.001'

def settle(position, price, timestamp):
    if timestamp<position.expires_at: raise Rejected('Not expired')
    entry,exit=Decimal(position.entry),Decimal(str(price))
    if exit<=0: raise Rejected('Invalid settlement quote')
    stake=Decimal(position.stake)
    win=(exit>entry if position.side=='BUY' else exit<entry)
    gross=Decimal(0) if exit==entry else stake*Decimal(position.payout) if win else -stake
    return gross-stake*Decimal(position.fee)

class PocketOption:
    name = 'Pocket Option (unverified)'
    verified = False
    async def execute(self, *args, **kwargs):
        raise Rejected('No verified official Pocket Option integration. Real execution disabled.')
