from alembic import op
import sqlalchemy as sa

revision = "2025_11_08_create_saved_searches"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "SavedSearches",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer),
        sa.Column("location", sa.String(255)),
        sa.Column("min_price", sa.Float),
        sa.Column("max_price", sa.Float),
        sa.Column("house_type", sa.String(50)),
        sa.Column("amenities", sa.ARRAY(sa.String)),
        sa.Column("bedrooms", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp())
    )
    op.execute("ALTER TABLE properties ADD COLUMN search_vector TSVECTOR")
    op.execute("UPDATE properties SET search_vector = to_tsvector('english', title || ' ' || description)")
    op.create_index("properties_search_idx", "properties", ["search_vector"], postgresql_using="gin")

def downgrade():
    op.drop_index("properties_search_idx", "Properties")
    op.drop_table("SavedSearches")
    op.execute("ALTER TABLE \"Properties\" DROP COLUMN search_vector")
