from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_11_11_add_max_distance_km_to_saved_searches'
down_revision = '2025_11_08_create_saved_searches'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('SavedSearches', sa.Column('max_distance_km', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('SavedSearches', 'max_distance_km')
