import os, time, secrets, hashlib, json
from datetime import datetime, timezone
from dataclasses import asdict
from decimal import Decimal
from typing import Literal
import jwt
import httpx
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DB
from .db import *
from .quant import analyze, backtest, walk_forward
from .trading import *
from .providers import market, gemini, SetupRequired

app=FastAPI(title='TradeMind AI OS',version='0.1.0')
bearer=HTTPBearer(); hasher=PasswordHasher()
def secret():
    value=os.getenv('JWT_SECRET','')
    if len(value)<32: raise HTTPException(503,'Configure JWT_SECRET (at least 32 characters)')
    return value
@app.exception_handler(SetupRequired)
async def setup_error(request,error):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=503,content={'detail':str(error)})
@app.exception_handler(httpx.HTTPError)
async def upstream_error(request,error):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=502,content={'detail':'Upstream provider unavailable; retry later'})
@app.middleware('http')
async def rate_limit(request,call_next):
    if os.getenv('REDIS_URL'):
        from redis.asyncio import from_url
        from fastapi.responses import JSONResponse
        try:
            async with from_url(os.environ['REDIS_URL']) as cache:
                key='rate:'+hashlib.sha256(request.client.host.encode()).hexdigest()+':'+str(int(time.time())//60)
                count=await cache.incr(key); await cache.expire(key,65)
                if count>120: return JSONResponse(status_code=429,content={'detail':'Rate limit exceeded'})
        except Exception:
            return JSONResponse(status_code=503,content={'detail':'Rate limiter unavailable'})
    return await call_next(request)
def user(credentials:HTTPAuthorizationCredentials=Depends(bearer),db:DB=Depends(db_session)):
    try:
        data=jwt.decode(credentials.credentials,secret(),algorithms=['HS256'],issuer='trademind',options={'require':['exp','sub','sid']})
        session=db.get(Session,int(data['sid']))
        if not session or session.revoked or session.expires<int(time.time()) or session.user_id!=int(data['sub']): raise ValueError()
        return int(data['sub'])
    except (jwt.PyJWTError,ValueError,TypeError): raise HTTPException(401,'Invalid or expired session')
def audit(db,uid,event,data=None): db.add(Audit(user_id=uid,data={'event':event,'details':data or {}}))
def tokens(db,uid):
    raw=secrets.token_urlsafe(48)
    s=Session(user_id=uid,digest=hashlib.sha256(raw.encode()).hexdigest(),expires=int(time.time())+604800)
    db.add(s); db.flush()
    token=jwt.encode({'sub':str(uid),'sid':str(s.id),'iss':'trademind','exp':int(time.time())+900},secret(),algorithm='HS256')
    return {'access_token':token,'refresh_token':raw,'token_type':'bearer'}
class Credentials(BaseModel):
    email:str=Field(min_length=5,max_length=254,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password:str=Field(min_length=12,max_length=128)
@app.post('/auth/register',status_code=201)
def register(body:Credentials,db:DB=Depends(db_session)):
    secret()
    email=body.email.strip().lower()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,'Account exists')
    u=User(email=email,password=hasher.hash(body.password)); db.add(u); db.flush(); db.add(Account(user_id=u.id)); result=tokens(db,u.id); audit(db,u.id,'register'); db.commit(); return result
@app.post('/auth/login')
def login(body:Credentials,db:DB=Depends(db_session)):
    u=db.scalar(select(User).where(User.email==body.email.strip().lower()))
    try:
        if not u: raise ValueError()
        hasher.verify(u.password,body.password)
    except (VerificationError,ValueError): raise HTTPException(401,'Invalid credentials')
    result=tokens(db,u.id); audit(db,u.id,'login'); db.commit(); return result
class Refresh(BaseModel): refresh_token:str
@app.post('/auth/refresh')
def refresh(body:Refresh,db:DB=Depends(db_session)):
    s=db.scalar(select(Session).where(Session.digest==hashlib.sha256(body.refresh_token.encode()).hexdigest()).with_for_update())
    if not s or s.revoked or s.expires<int(time.time()): raise HTTPException(401,'Invalid refresh token')
    s.revoked=True; result=tokens(db,s.user_id); db.commit(); return result
@app.post('/auth/logout')
def logout(uid=Depends(user),db:DB=Depends(db_session)):
    for s in db.scalars(select(Session).where(Session.user_id==uid)): s.revoked=True
    audit(db,uid,'revoke_all_sessions'); db.commit(); return {'ok':True}
@app.get('/health')
def health(db:DB=Depends(db_session)):
    db.execute(select(1)); return {'status':'ok','real_trading_enabled':False}
@app.get('/account')
def account(uid=Depends(user),db:DB=Depends(db_session)):
    a=db.scalar(select(Account).where(Account.user_id==uid))
    return {'balance':str(a.balance),'mode':'SIMULATED','halted':a.halted,'real_trading_enabled':False}
@app.get('/market')
async def candles(symbol:str='EUR/USD',interval:Literal['1min','5min','15min','1h']='1min',uid=Depends(user)):
    return {'source':'Twelve Data','candles':[asdict(c) for c in await market(symbol,interval)]}
@app.get('/signals')
async def signals(symbol:str='EUR/USD',uid=Depends(user),db:DB=Depends(db_session)):
    result=analyze(await market(symbol),symbol); db.add(Signal(user_id=uid,data=result)); db.commit(); return result
@app.get('/analysis/multi')
async def multi(symbol:str='EUR/USD',uid=Depends(user)):
    result={}
    for interval in ('1min','5min','15min','1h'): result[interval]=analyze(await market(symbol,interval),symbol,interval)
    return result
class Order(BaseModel):
    symbol:str=Field(default='EUR/USD',max_length=30)
    side:Literal['BUY','SELL']
    stake:float=Field(gt=0,le=100000)
    expiry:int=Field(default=300,ge=60,le=3600)
    idempotency_key:str=Field(min_length=16,max_length=100)
def locked_account(db,uid): return db.scalar(select(Account).where(Account.user_id==uid).with_for_update())
@app.post('/demo/orders')
async def order(body:Order,uid=Depends(user),db:DB=Depends(db_session)):
    bars=await market(body.symbol)
    a=locked_account(db,uid)
    trades=list(db.scalars(select(Trade).where(Trade.user_id==uid).order_by(Trade.id)))
    for t in trades:
        if t.data.get('idempotency_key')==body.idempotency_key: return {'id':t.id,**t.data}
    now=int(time.time()); today=datetime.now(timezone.utc).date().isoformat()
    daily=[t for t in trades if t.data['day']==today]
    pnl=sum(float(t.data.get('pnl',0)) for t in daily)
    losses=0
    for t in reversed(trades):
        if t.data['status']=='closed' and float(t.data['pnl'])<0: losses+=1
        elif t.data['status']=='closed': break
    limits=get_risk(uid,db)
    balance=float(a.balance); reserved=sum(float(t.data['stake']) for t in trades if t.data['status'] in ('open','pending'))
    try: validate_risk(balance-reserved,10000,float(a.peak),pnl-reserved,body.stake*1.001,len([t for t in trades if t.data['status'] in ('open','pending')]),losses,len(daily),a.halted,Risk(**limits))
    except Rejected as e: raise HTTPException(409,str(e))
    # A market order is filled on the first minute boundary after assumed 1s latency.
    fill_at=((now+1+59)//60)*60
    expiry_at=((fill_at+body.expiry+59)//60)*60
    data={**body.model_dump(),'entry':None,'opened_at':fill_at,'expires_at':expiry_at,'payout':'0.8','fee':'0.001','status':'pending','day':today,'mode':'SIMULATED','data_timestamp':bars[-1].timestamp,'fill_model':'next observed minute open after 1s latency + 2bps adverse slippage; expiry rounded up to minute'}
    t=Trade(user_id=uid,data=data); db.add(t); audit(db,uid,'demo_open',data); db.commit(); return {'id':t.id,**data}
@app.post('/demo/settle')
async def settlement(uid=Depends(user),db:DB=Depends(db_session)):
    # Fetch first, then serialize account changes. Missing expiry bars never settle at arbitrary prices.
    open_trades=list(db.scalars(select(Trade).where(Trade.user_id==uid)))
    feeds={}
    for t in open_trades:
        if t.data['status'] in ('open','pending'): feeds[t.data['symbol']]=await market(t.data['symbol'],size=5000)
    a=locked_account(db,uid); db.expire_all(); closed=[]
    for t in db.scalars(select(Trade).where(Trade.user_id==uid).with_for_update()):
        d=dict(t.data)
        if d['status'] not in ('open','pending'): continue
        feed=feeds.get(d['symbol'],[])
        if d['status']=='pending':
            fill=next((c for c in feed if c.timestamp==d['opened_at']),None)
            if not fill: continue
            d['entry']=str(fill.open*(1.0002 if d['side']=='BUY' else .9998))
            d['status']='open';t.data=dict(d);audit(db,uid,'demo_fill',d)
        if d['expires_at']>time.time(): continue
        bar=next((c for c in feeds.get(d['symbol'],[]) if c.timestamp==((d['expires_at']+59)//60)*60),None)
        if not bar: continue
        p=Position(d['side'],str(d['stake']),d['entry'],d['opened_at'],d['expires_at'],d['payout'],d['fee'])
        pnl=settle(p,bar.open,bar.timestamp); a.balance=Decimal(str(a.balance))+pnl; a.peak=max(a.peak,a.balance)
        t.data={**d,'status':'closed','exit':str(bar.open),'pnl':str(pnl),'settled_at':bar.timestamp}; audit(db,uid,'demo_settle',t.data); closed.append(t.id)
    if float(a.balance)<=9000: a.halted=True
    db.commit(); return {'closed':closed}
@app.get('/demo/history')
def history(uid=Depends(user),db:DB=Depends(db_session)):
    return [{'id':t.id,**t.data} for t in db.scalars(select(Trade).where(Trade.user_id==uid).order_by(Trade.id.desc()))]
@app.post('/risk/stop')
def stop(uid=Depends(user),db:DB=Depends(db_session)):
    a=locked_account(db,uid); a.halted=True; audit(db,uid,'emergency_stop'); db.commit(); return {'halted':True}
@app.post('/research/backtest')
async def research(symbol:str='EUR/USD',uid=Depends(user),db:DB=Depends(db_session)):
    data=await market(symbol,size=1000); result={'backtest':backtest(data),'walk_forward':walk_forward(data)}; db.add(Backtest(user_id=uid,data=result)); db.commit(); return result
class Chat(BaseModel): message:str=Field(min_length=1,max_length=8000)
@app.post('/assistant')
async def assistant(body:Chat,uid=Depends(user),db:DB=Depends(db_session)):
    a=db.scalar(select(Account).where(Account.user_id==uid))
    recent=db.scalar(select(Signal).where(Signal.user_id==uid).order_by(Signal.id.desc()))
    context={'mode':'SIMULATED','balance':str(a.balance),'halted':a.halted,'performance':performance(uid,db),'latest_signal':recent.data if recent else None}
    reply=await gemini(body.message,context)
    db.add(Conversation(user_id=uid,data={'message':body.message,'reply':reply})); db.commit(); return {'reply':reply}
class Design(BaseModel):
    name:str=Field(max_length=200)
    canvas:dict
@app.post('/design/projects')
def save_design(body:Design,uid=Depends(user),db:DB=Depends(db_session)):
    if len(json.dumps(body.canvas))>1000000: raise HTTPException(413,'Canvas too large')
    p=Project(user_id=uid,data=body.model_dump()); db.add(p); db.commit(); return {'id':p.id}
@app.get('/design/projects')
def projects(uid=Depends(user),db:DB=Depends(db_session)):
    return [{'id':p.id,**p.data} for p in db.scalars(select(Project).where(Project.user_id==uid))]
@app.post('/design/generate')
async def generate(body:Chat,uid=Depends(user),db:DB=Depends(db_session)):
    key=os.getenv('OPENAI_IMAGE_API_KEY')
    if not key: raise SetupRequired('Configure OPENAI_IMAGE_API_KEY for image generation')
    async with httpx.AsyncClient(timeout=180) as client:
        r=await client.post('https://api.openai.com/v1/images/generations',headers={'Authorization':'Bearer '+key},json={'model':'gpt-image-1','prompt':body.message,'size':'1024x1024'})
        r.raise_for_status(); data=r.json()['data'][0]
    return data
@app.post('/real/orders')
def real(uid=Depends(user)): raise HTTPException(403,'Real trading disabled: official broker integration not verified')
@app.websocket('/ws/market')
async def websocket(ws:WebSocket):
    import asyncio
    await ws.accept()
    try:
        auth=await asyncio.wait_for(ws.receive_json(),timeout=10)
        with SessionLocal() as db: user(HTTPAuthorizationCredentials(scheme='Bearer',credentials=auth.get('token','')),db)
        while True:
            try: await ws.send_json({'source':'Twelve Data REST polling via WebSocket','candles':[asdict(c) for c in await market('EUR/USD')]})
            except (SetupRequired,httpx.HTTPError) as e: await ws.send_json({'error':str(e) if isinstance(e,SetupRequired) else 'Provider unavailable'})
            await asyncio.sleep(60)
    except (WebSocketDisconnect,asyncio.TimeoutError): pass
    except HTTPException: await ws.close(code=4401)
class Automation(BaseModel):
    enabled:bool
    symbol:str=Field(default='EUR/USD',max_length=30)
@app.post('/demo/automation')
def automation(body:Automation,uid=Depends(user),db:DB=Depends(db_session)):
    locked_account(db,uid)
    setting=db.scalar(select(RiskSetting).where(RiskSetting.user_id==uid))
    if not setting: setting=RiskSetting(user_id=uid);db.add(setting)
    setting.data={**(setting.data or {}),'autonomous_demo':body.enabled,'symbol':body.symbol}
    audit(db,uid,'automation_changed',setting.data);db.commit();return setting.data
@app.get('/worker/status')
async def worker_status(uid=Depends(user)):
    if not os.getenv('REDIS_URL'): raise SetupRequired('Configure REDIS_URL and start worker')
    from redis.asyncio import from_url
    async with from_url(os.environ['REDIS_URL']) as cache: heartbeat=await cache.get('demo-worker-heartbeat')
    return {'healthy':bool(heartbeat and time.time()-float(heartbeat)<180)}
@app.post('/research/optimize')
async def optimization(symbol:str='EUR/USD',uid=Depends(user),db:DB=Depends(db_session)):
    from .research import optimize, calibrate
    bars=await market(symbol,size=1000)
    result={'optimization':optimize(bars),'calibration':calibrate(bars)}
    db.add(Strategy(user_id=uid,data={'symbol':symbol,**result}));db.commit();return result
class RemoveBackground(BaseModel):
    image_base64:str=Field(max_length=14000000)
@app.post('/design/remove-background')
async def remove_background(body:RemoveBackground,uid=Depends(user)):
    import base64, binascii
    key=os.getenv('REMOVE_BG_API_KEY')
    if not key:raise SetupRequired('Configure REMOVE_BG_API_KEY to enable background removal')
    try:image=base64.b64decode(body.image_base64,validate=True)
    except binascii.Error:raise HTTPException(422,'Invalid base64 image')
    async with httpx.AsyncClient(timeout=90) as client:
        response=await client.post('https://api.remove.bg/v1.0/removebg',headers={'X-Api-Key':key},files={'image_file':('image.png',image,'image/png')},data={'size':'auto'})
        response.raise_for_status()
    return {'image_base64':base64.b64encode(response.content).decode()}
class RiskInput(BaseModel):
    per_trade:float=Field(default=.01,gt=0,le=.01)
    daily_loss:float=Field(default=.03,gt=0,le=.03)
    drawdown:float=Field(default=.10,gt=0,le=.10)
    max_positions:int=Field(default=1,ge=1,le=1)
    max_losses:int=Field(default=3,ge=1,le=3)
    daily_trades:int=Field(default=10,ge=1,le=10)
@app.get('/risk')
def get_risk(uid=Depends(user),db:DB=Depends(db_session)):
    setting=db.scalar(select(RiskSetting).where(RiskSetting.user_id==uid))
    return {**asdict(Risk()),**(setting.data.get('limits',{}) if setting else {})}
@app.post('/risk')
def set_risk(body:RiskInput,uid=Depends(user),db:DB=Depends(db_session)):
    locked_account(db,uid)
    setting=db.scalar(select(RiskSetting).where(RiskSetting.user_id==uid))
    if not setting:setting=RiskSetting(user_id=uid,data={});db.add(setting)
    setting.data={**setting.data,'limits':body.model_dump()};audit(db,uid,'risk_changed',body.model_dump());db.commit();return body
@app.get('/performance')
def performance(uid=Depends(user),db:DB=Depends(db_session)):
    from .quant import metrics
    trades=list(db.scalars(select(Trade).where(Trade.user_id==uid).order_by(Trade.id)))
    returns=[float(t.data['pnl']) for t in trades if t.data['status']=='closed']
    equity=[];balance=10000
    for value in returns:balance+=value;equity.append(balance)
    return {'mode':'SIMULATED','metrics':metrics(returns),'equity':equity,'reserved':sum(float(t.data['stake'])*1.001 for t in trades if t.data['status'] in ('pending','open'))}
