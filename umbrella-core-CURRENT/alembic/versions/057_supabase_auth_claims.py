"""Use Supabase Auth identities and signed claims for dashboard authorization.

Revision ID: 057_supabase_auth_claims
Revises:     056_bot_guild_config
"""

from alembic import op
import sqlalchemy as sa

revision = "057_supabase_auth_claims"
down_revision = "056_bot_guild_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "supabase_auth_id" not in user_columns:
        op.add_column(
            "users",
            sa.Column("supabase_auth_id", sa.String(length=36), nullable=True),
        )
    if "authz_version" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "authz_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_supabase_auth_id" not in indexes:
        op.create_index(
            "ix_users_supabase_auth_id",
            "users",
            ["supabase_auth_id"],
            unique=True,
        )

    if inspector.has_table("sessions") and "revoked" in {
        column["name"] for column in inspector.get_columns("sessions")
    }:
        op.execute("UPDATE sessions SET revoked = TRUE WHERE revoked = FALSE")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
        RETURNS jsonb
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
            staff_user record;
            claims jsonb;
            metadata jsonb;
        BEGIN
            SELECT
                u.id,
                u.is_active,
                u.authz_version,
                r.name AS role_name,
                COALESCE((
                    SELECT array_agg(DISTINCT granted.permission_key)
                    FROM (
                        SELECT p.permission_key
                        FROM public.role_permissions rp
                        JOIN public.permissions p ON p.id = rp.permission_id
                        WHERE rp.role_id = u.role_id
                        UNION
                        SELECT jsonb_array_elements_text(
                            COALESCE(u.extra_permissions::jsonb, '[]'::jsonb)
                        )
                    ) AS granted
                ), ARRAY[]::text[]) AS permission_keys
            INTO staff_user
            FROM auth.identities i
            JOIN public.users u ON u.discord_id = i.provider_id
            LEFT JOIN public.roles r ON r.id = u.role_id
            WHERE i.user_id = (event->>'user_id')::uuid
              AND i.provider = 'discord'
            LIMIT 1;

            IF NOT FOUND THEN
                RETURN jsonb_build_object(
                    'error',
                    jsonb_build_object(
                        'http_code', 403,
                        'message', 'No active UmbrellaOS staff account is linked to this Discord identity'
                    )
                );
            END IF;

            IF NOT staff_user.is_active THEN
                RETURN jsonb_build_object(
                    'error',
                    jsonb_build_object(
                        'http_code', 403,
                        'message', 'No active UmbrellaOS staff account is linked to this Discord identity'
                    )
                );
            END IF;

            claims := event->'claims';
            metadata := COALESCE(claims->'app_metadata', '{}'::jsonb)
                || jsonb_build_object(
                    'umbrella_user_id', staff_user.id,
                    'umbrella_role', staff_user.role_name,
                    'umbrella_permissions', to_jsonb(staff_user.permission_keys),
                    'umbrella_authz_version', staff_user.authz_version
                );
            claims := jsonb_set(claims, '{app_metadata}', metadata, true);

            RETURN jsonb_set(event, '{claims}', claims, true);
        END;
        $function$;
        """
    )
    op.execute(
        """
        REVOKE ALL ON FUNCTION public.custom_access_token_hook(jsonb)
            FROM PUBLIC, anon, authenticated
        """
    )
    op.execute(
        """
        GRANT EXECUTE ON FUNCTION public.custom_access_token_hook(jsonb)
            TO supabase_auth_admin
        """
    )
    op.execute(
        """
        GRANT SELECT ON public.users, public.roles, public.permissions,
            public.role_permissions TO supabase_auth_admin
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.custom_access_token_hook(jsonb)")
    op.execute(
        """
        REVOKE SELECT ON public.users, public.roles, public.permissions,
            public.role_permissions FROM supabase_auth_admin
        """
    )
    op.drop_index("ix_users_supabase_auth_id", table_name="users")
    op.drop_column("users", "authz_version")
    op.drop_column("users", "supabase_auth_id")
