from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('exam_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('detector', sa.String(length=63), nullable=False),
    sa.Column('threat', sa.String(length=32), nullable=False),
    sa.Column('exam', sa.String(length=63), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.Column('state', sa.String(length=16), nullable=False),
    sa.Column('flagged', sa.Integer(), nullable=True),
    sa.Column('caught', sa.Integer(), nullable=True),
    sa.Column('poisoned', sa.Integer(), nullable=True),
    sa.Column('precision', sa.Float(), nullable=True),
    sa.Column('recall', sa.Float(), nullable=True),
    sa.Column('f1', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('exam_results')
