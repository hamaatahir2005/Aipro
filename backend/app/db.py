import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, JSON, DateTime, ForeignKey, Numeric, Integer, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

class Base(DeclarativeBase): pass
class Record(Base):
    __abstract__=True
    id: Mapped[int]=mapped_column(primary_key=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class User(Record):
    __tablename__='users'
    email: Mapped[str]=mapped_column(String(254),unique=True)
    password: Mapped[str]=mapped_column(String)
class Session(Record):
    __tablename__='sessions'
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    digest: Mapped[str]=mapped_column(String,unique=True)
    expires: Mapped[int]=mapped_column(Integer)
    revoked: Mapped[bool]=mapped_column(Boolean,default=False)
class Account(Record):
    __tablename__='trading_accounts'
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),unique=True)
    balance: Mapped[float]=mapped_column(Numeric(18,6),default=10000)
    peak: Mapped[float]=mapped_column(Numeric(18,6),default=10000)
    halted: Mapped[bool]=mapped_column(Boolean,default=False)
class Document(Record):
    __abstract__=True
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    data: Mapped[dict]=mapped_column(JSON,default=dict)
class Instrument(Record):
    __tablename__='market_instruments'
    symbol: Mapped[str]=mapped_column(String,unique=True)
    data: Mapped[dict]=mapped_column(JSON)
class History(Record):
    __tablename__='historical_market_data'
    symbol: Mapped[str]=mapped_column(String,index=True)
    data: Mapped[dict]=mapped_column(JSON)
class Strategy(Document): __tablename__='trading_strategies'
class Signal(Document): __tablename__='trading_signals'
class Trade(Document): __tablename__='demo_transactions'
class RealTrade(Document): __tablename__='real_transactions'
class RiskSetting(Document): __tablename__='risk_settings'
class Backtest(Document): __tablename__='backtesting_results'
class Conversation(Document): __tablename__='ai_conversations'
class Project(Document): __tablename__='graphic_design_projects'
class Asset(Document): __tablename__='generated_image_assets'
class Audit(Document): __tablename__='audit_logs'
engine=create_engine(os.environ.get('DATABASE_URL','sqlite:///./development.db'))
SessionLocal=sessionmaker(engine,expire_on_commit=False)
def db_session():
    with SessionLocal() as session: yield session
