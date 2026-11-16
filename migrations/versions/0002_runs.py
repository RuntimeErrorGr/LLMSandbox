from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_name', sa.String(length=63), nullable=False),
    sa.Column('module', sa.String(length=63), nullable=False),
    sa.Column('namespace', sa.String(length=63), nullable=False),
    sa.Column('params', sa.JSON(), nullable=False),
    sa.Column('state', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('job_name')
    )


def downgrade() -> None:
    op.drop_table('runs')
