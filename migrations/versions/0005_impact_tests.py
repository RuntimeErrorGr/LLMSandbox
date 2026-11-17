from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('impact_tests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('suspect', sa.String(length=63), nullable=False),
    sa.Column('clean', sa.String(length=63), nullable=False),
    sa.Column('detector', sa.String(length=63), nullable=False),
    sa.Column('state', sa.String(length=16), nullable=False),
    sa.Column('step', sa.String(length=120), nullable=False),
    sa.Column('removed', sa.JSON(), nullable=False),
    sa.Column('results', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('impact_tests')
