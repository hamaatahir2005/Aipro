"""Isolated API tests. Requires installed requirements; no live provider calls."""
import os
os.environ['DATABASE_URL']='sqlite://'
os.environ['JWT_SECRET']='test-only-secret-that-is-longer-than-32-characters'
os.environ.pop('REDIS_URL',None)
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app import main
from app.db import Base,SessionLocal
from unittest.mock import AsyncMock
import pytest

@pytest.fixture
def client(monkeypatch):
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal.configure(bind=engine)
    def get_db():
        with SessionLocal() as db:yield db
    main.app.dependency_overrides[main.db_session]=get_db
    monkeypatch.setattr(main,'market',AsyncMock(side_effect=main.SetupRequired('Provider not configured')))
    with TestClient(main.app) as c:yield c
    main.app.dependency_overrides.clear();Base.metadata.drop_all(engine);engine.dispose()

def auth(client,email='test@example.com'):
    r=client.post('/auth/register',json={'email':email,'password':'long-password-123'})
    assert r.status_code==201,r.text
    return r.json(),{'Authorization':'Bearer '+r.json()['access_token']}

def test_auth_rotation_and_revocation(client):
    t,h=auth(client)
    assert client.get('/account',headers=h).json()['mode']=='SIMULATED'
    r=client.post('/auth/refresh',json={'refresh_token':t['refresh_token']});assert r.status_code==200
    assert client.post('/auth/refresh',json={'refresh_token':t['refresh_token']}).status_code==401
    assert client.get('/account',headers=h).status_code==401
    h={'Authorization':'Bearer '+r.json()['access_token']}
    assert client.post('/auth/logout',headers=h).status_code==200
    assert client.get('/account',headers=h).status_code==401

def test_fail_closed_and_ownership(client):
    _,h=auth(client)
    assert client.get('/account').status_code==403
    assert client.post('/real/orders',headers=h,json={}).status_code==403
    assert client.get('/market',headers=h).status_code==503
    assert client.post('/risk/stop',headers=h,json={}).json()['halted']
    p=client.post('/design/projects',headers=h,json={'name':'brand','canvas':{'layers':[]}});assert p.status_code==200
    _,other=auth(client,'other@example.com')
    assert client.get('/design/projects',headers=other).json()==[]

def test_validation(client):
    _,h=auth(client)
    assert client.post('/demo/orders',headers=h,json={'stake':-1}).status_code==422
    assert client.post('/auth/login',json={'email':'test@example.com','password':'incorrect-password'}).status_code==401
