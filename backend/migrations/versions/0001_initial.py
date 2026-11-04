"""Initial schema, revision 0001. Schema frozen explicitly for future migrations."""
from alembic import op
import sqlalchemy as sa
revision='0001'
down_revision=None
branch_labels=None
depends_on=None

def common():
    return [sa.Column('id',sa.Integer(),primary_key=True),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False)]
def upgrade():
    op.create_table('users',*common(),sa.Column('email',sa.String(254),unique=True,nullable=False),sa.Column('password',sa.String(),nullable=False))
    op.create_table('sessions',*common(),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('digest',sa.String(),unique=True,nullable=False),sa.Column('expires',sa.Integer(),nullable=False),sa.Column('revoked',sa.Boolean(),nullable=False))
    op.create_table('trading_accounts',*common(),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),unique=True,nullable=False),sa.Column('balance',sa.Numeric(18,6),nullable=False),sa.Column('peak',sa.Numeric(18,6),nullable=False),sa.Column('halted',sa.Boolean(),nullable=False))
    for table in ['trading_strategies','trading_signals','demo_transactions','real_transactions','risk_settings','backtesting_results','ai_conversations','graphic_design_projects','generated_image_assets','audit_logs']:
        op.create_table(table,*common(),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('data',sa.JSON(),nullable=False))
        op.create_index('ix_'+table+'_user_id',table,['user_id'])
    for table in ['market_instruments','historical_market_data']:
        op.create_table(table,*common(),sa.Column('symbol',sa.String(),nullable=False,unique=table=='market_instruments'),sa.Column('data',sa.JSON(),nullable=False))
def downgrade():
    for table in ['audit_logs','generated_image_assets','graphic_design_projects','ai_conversations','backtesting_results','risk_settings','real_transactions','demo_transactions','trading_signals','trading_strategies','historical_market_data','market_instruments','trading_accounts','sessions','users']:op.drop_table(table)
