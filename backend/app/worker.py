"""Opt-in autonomous demo worker. Never invokes a real broker."""
import asyncio, os, time, logging, secrets
from redis.asyncio import from_url
from sqlalchemy import select
from .db import SessionLocal, RiskSetting, Audit
from .main import order, settlement, Order
from .providers import market
from .quant import analyze
logging.basicConfig(level=logging.INFO)
async def tick():
    with SessionLocal() as db:
        settings=list(db.scalars(select(RiskSetting)))
        for setting in settings:
            if not setting.data.get('autonomous_demo'): continue
            uid=setting.user_id
            try:
                await settlement(uid,db)
                symbol=setting.data.get('symbol','EUR/USD')
                signal=analyze(await market(symbol),symbol)
                if signal['recommendation']!='HOLD':
                    await order(Order(symbol=symbol,side=signal['recommendation'],stake=50,expiry=300,idempotency_key=f'auto-{uid}-{symbol}-{signal["timestamp"]}'),uid,db)
            except Exception as exc:
                db.rollback();db.add(Audit(user_id=uid,data={'event':'worker_error','type':type(exc).__name__}));db.commit()
                logging.warning('Demo worker operation blocked for user %s: %s',uid,type(exc).__name__)
async def main():
    async with from_url(os.environ['REDIS_URL']) as redis:
        while True:
            token=secrets.token_hex(16)
            lock=await redis.set('demo-worker-lock',token,nx=True,ex=300)
            if lock:
                try:
                    await asyncio.wait_for(tick(),timeout=240);await redis.set('demo-worker-heartbeat',str(time.time()),ex=180)
                except Exception as exc:
                    logging.error('Worker tick failed: %s',type(exc).__name__)
                finally:
                    await redis.eval("if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end",1,'demo-worker-lock',token)
            await asyncio.sleep(60)
if __name__=='__main__': asyncio.run(main())
