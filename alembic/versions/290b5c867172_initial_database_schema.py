"""Initial database schema

Revision ID: 290b5c867172
Revises: 
Create Date: 2025-11-08 14:05:18.637198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '290b5c867172'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create goals table
    op.create_table(
        'goals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'BLOCKED', name='goalstatus'), nullable=False),
        sa.Column('mode', sa.Enum('ONE_TIME', 'CONTINUOUS', name='goalmode'), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['goals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_goals_id'), 'goals', ['id'], unique=False)

    # Create agent_states table
    op.create_table(
        'agent_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('is_running', sa.Boolean(), nullable=False),
        sa.Column('current_goal_id', sa.String(), nullable=True),
        sa.Column('mode', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['current_goal_id'], ['goals.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id')
    )
    op.create_index(op.f('ix_agent_states_agent_id'), 'agent_states', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_states_id'), 'agent_states', ['id'], unique=False)

    # Create memories table
    op.create_table(
        'memories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('memory_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding_id', sa.String(), nullable=True),
        sa.Column('importance', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('accessed_at', sa.DateTime(), nullable=False),
        sa.Column('access_count', sa.Integer(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memories_agent_id'), 'memories', ['agent_id'], unique=False)
    op.create_index(op.f('ix_memories_embedding_id'), 'memories', ['embedding_id'], unique=False)
    op.create_index(op.f('ix_memories_id'), 'memories', ['id'], unique=False)
    op.create_index(op.f('ix_memories_memory_type'), 'memories', ['memory_type'], unique=False)

    # Create actions table
    op.create_table(
        'actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('goal_id', sa.String(), nullable=True),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('action_data', sa.JSON(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_actions_agent_id'), 'actions', ['agent_id'], unique=False)
    op.create_index(op.f('ix_actions_id'), 'actions', ['id'], unique=False)

    # Create metric_snapshots table
    op.create_table(
        'metric_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('metric_type', sa.String(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_metric_snapshots_agent_id'), 'metric_snapshots', ['agent_id'], unique=False)
    op.create_index(op.f('ix_metric_snapshots_id'), 'metric_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_metric_snapshots_metric_type'), 'metric_snapshots', ['metric_type'], unique=False)
    op.create_index(op.f('ix_metric_snapshots_timestamp'), 'metric_snapshots', ['timestamp'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_metric_snapshots_timestamp'), table_name='metric_snapshots')
    op.drop_index(op.f('ix_metric_snapshots_metric_type'), table_name='metric_snapshots')
    op.drop_index(op.f('ix_metric_snapshots_id'), table_name='metric_snapshots')
    op.drop_index(op.f('ix_metric_snapshots_agent_id'), table_name='metric_snapshots')
    op.drop_table('metric_snapshots')
    
    op.drop_index(op.f('ix_actions_id'), table_name='actions')
    op.drop_index(op.f('ix_actions_agent_id'), table_name='actions')
    op.drop_table('actions')
    
    op.drop_index(op.f('ix_memories_memory_type'), table_name='memories')
    op.drop_index(op.f('ix_memories_id'), table_name='memories')
    op.drop_index(op.f('ix_memories_embedding_id'), table_name='memories')
    op.drop_index(op.f('ix_memories_agent_id'), table_name='memories')
    op.drop_table('memories')
    
    op.drop_index(op.f('ix_agent_states_id'), table_name='agent_states')
    op.drop_index(op.f('ix_agent_states_agent_id'), table_name='agent_states')
    op.drop_table('agent_states')
    
    op.drop_index(op.f('ix_goals_id'), table_name='goals')
    op.drop_table('goals')
