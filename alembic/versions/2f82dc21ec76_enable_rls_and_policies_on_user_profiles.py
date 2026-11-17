"""Enable RLS and policies on user_profiles

Revision ID: 2f82dc21ec76
Revises: acd57b2dc881
Create Date: 2026-11-16 17:36:50.654124

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '2f82dc21ec76'
down_revision: Union[str, Sequence[str], None] = 'acd57b2dc881'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
      # 1. Enable RLS on the table (blocks all direct anon/authenticated access by default)
    op.execute("ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;")

    # 2. Allow authenticated users to read their own profile
    op.execute("""
        CREATE POLICY "Users can view their own profile"
        ON public.user_profiles
        FOR SELECT
        TO authenticated
        USING ((SELECT auth.uid()) = id);
    """)

    # 3. Allow authenticated users to update their own profile
    op.execute("""
        CREATE POLICY "Users can update their own profile"
        ON public.user_profiles
        FOR UPDATE
        TO authenticated
        USING ((SELECT auth.uid()) = id)
        WITH CHECK ((SELECT auth.uid()) = id);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP POLICY IF EXISTS "Users can update their own profile" ON public.user_profiles;')
    op.execute('DROP POLICY IF EXISTS "Users can view their own profile" ON public.user_profiles;')
    op.execute("ALTER TABLE public.user_profiles DISABLE ROW LEVEL SECURITY;")
