from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
from psycopg import sql

DEFAULT_DATABASE_URL = "postgresql:///engram"
DEFAULT_BROKER_ROLE = "engram_grounding_broker"
DEFAULT_PASSWORD_ENV = "ENGRAM_GROUNDING_BROKER_PASSWORD"

BROKER_SELECT_TABLES: tuple[str, ...] = (
    "claim_grounding_requests",
    "claim_grounding_grants",
    "claim_grounding_network_dispatches",
    "claim_grounding_grant_uses",
    "claim_grounding_responses",
    "claim_grounding_links",
    "entity_grounding_evidence",
)

BROKER_INSERT_TABLES: tuple[str, ...] = (
    "claim_grounding_network_dispatches",
    "claim_grounding_grant_uses",
    "claim_grounding_responses",
    "claim_grounding_links",
    "entity_grounding_evidence",
    "entity_identity_review_actions",
)

RAW_CORPUS_TABLES: tuple[str, ...] = (
    "conversations",
    "messages",
    "segments",
    "captures",
    "claims",
    "beliefs",
)


class GroundingBrokerProvisioningError(RuntimeError):
    """Raised when the broker role cannot be safely provisioned."""


@dataclass(frozen=True)
class GroundingBrokerProvisioningResult:
    """Summary of one broker-role provisioning run."""

    role_name: str
    login_enabled: bool
    password_configured: bool
    suggested_database_url: str


def provision_grounding_broker_role(
    conn: psycopg.Connection,
    *,
    role_name: str = DEFAULT_BROKER_ROLE,
    login: bool = True,
    password: str | None = None,
    database_url_for_suggestion: str = DEFAULT_DATABASE_URL,
) -> GroundingBrokerProvisioningResult:
    """Create or update the restricted grounding-broker PostgreSQL role."""
    _validate_role_name(role_name)
    _assert_required_tables_present(conn)
    role = sql.Identifier(role_name)
    conn.execute(
        """
        SELECT pg_advisory_xact_lock(
            hashtextextended('engram_grounding_broker_role', 0)
        )
        """
    )
    conn.execute(
        sql.SQL(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {role_literal}) THEN
                    CREATE ROLE {role};
                END IF;
            END
            $$;
            """
        ).format(role=role, role_literal=sql.Literal(role_name))
    )
    conn.execute(
        sql.SQL("ALTER ROLE {} WITH {} NOINHERIT").format(
            role,
            sql.SQL("LOGIN") if login else sql.SQL("NOLOGIN"),
        )
    )
    if password is not None:
        if password == "":
            raise GroundingBrokerProvisioningError("broker password must not be empty")
        conn.execute(sql.SQL("ALTER ROLE {} PASSWORD %s").format(role), (password,))

    _revoke_public_table_privileges(conn, role_name)
    conn.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(role))
    conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
    for table_name in BROKER_SELECT_TABLES:
        conn.execute(
            sql.SQL("GRANT SELECT ON TABLE {} TO {}").format(
                sql.Identifier(table_name),
                role,
            )
        )
    for table_name in BROKER_INSERT_TABLES:
        conn.execute(
            sql.SQL("GRANT INSERT ON TABLE {} TO {}").format(
                sql.Identifier(table_name),
                role,
            )
        )
    _assert_no_raw_corpus_reads(conn, role_name)
    _assert_no_mutation_privileges(conn, role_name)
    return GroundingBrokerProvisioningResult(
        role_name=role_name,
        login_enabled=login,
        password_configured=password is not None,
        suggested_database_url=suggest_broker_database_url(
            database_url_for_suggestion,
            role_name=role_name,
        ),
    )


def suggest_broker_database_url(database_url: str, *, role_name: str) -> str:
    """Return a broker DSN suggestion without embedding a password."""
    parts = urlsplit(database_url or DEFAULT_DATABASE_URL)
    if parts.scheme not in {"postgresql", "postgres"}:
        return database_url
    if not parts.netloc:
        separator = "&" if parts.query else ""
        query = f"{parts.query}{separator}user={quote(role_name)}"
        suffix = f"?{query}" if query else ""
        fragment = f"#{parts.fragment}" if parts.fragment else ""
        return f"{parts.scheme}://{parts.path}{suffix}{fragment}"
    host = parts.hostname or ""
    port = f":{parts.port}" if parts.port is not None else ""
    netloc = f"{quote(role_name)}@{host}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _revoke_public_table_privileges(conn: psycopg.Connection, role_name: str) -> None:
    role = sql.Identifier(role_name)
    rows = conn.execute(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
        """
    ).fetchall()
    for (table_name,) in rows:
        conn.execute(
            sql.SQL("REVOKE ALL PRIVILEGES ON TABLE {} FROM {}").format(
                sql.Identifier(str(table_name)),
                role,
            )
        )


def _assert_required_tables_present(conn: psycopg.Connection) -> None:
    expected = set(BROKER_SELECT_TABLES) | set(BROKER_INSERT_TABLES) | set(RAW_CORPUS_TABLES)
    rows = conn.execute(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename = ANY(%s)
        """,
        (list(expected),),
    ).fetchall()
    present = {str(row[0]) for row in rows}
    missing = sorted(expected - present)
    if missing:
        raise GroundingBrokerProvisioningError(
            "database is not migrated for grounding broker provisioning; "
            f"missing table(s): {', '.join(missing)}"
        )


def _assert_no_raw_corpus_reads(conn: psycopg.Connection, role_name: str) -> None:
    allowed = [
        table_name
        for table_name in RAW_CORPUS_TABLES
        if _has_table_privilege(conn, role_name, table_name, "SELECT")
    ]
    if allowed:
        raise GroundingBrokerProvisioningError(
            "broker role unexpectedly has raw-corpus SELECT privilege on: "
            f"{', '.join(allowed)}"
        )


def _assert_no_mutation_privileges(conn: psycopg.Connection, role_name: str) -> None:
    forbidden: list[str] = []
    scoped_tables = set(BROKER_SELECT_TABLES) | set(BROKER_INSERT_TABLES) | set(RAW_CORPUS_TABLES)
    for table_name in scoped_tables:
        for privilege in ("UPDATE", "DELETE", "TRUNCATE"):
            if _has_table_privilege(conn, role_name, table_name, privilege):
                forbidden.append(f"{table_name}:{privilege}")
    if forbidden:
        raise GroundingBrokerProvisioningError(
            "broker role unexpectedly has destructive privilege(s): "
            f"{', '.join(sorted(forbidden))}"
        )


def _has_table_privilege(
    conn: psycopg.Connection,
    role_name: str,
    table_name: str,
    privilege: str,
) -> bool:
    row = conn.execute(
        "SELECT has_table_privilege(%s, %s, %s)",
        (role_name, f"public.{table_name}", privilege),
    ).fetchone()
    if row is None:
        raise GroundingBrokerProvisioningError("privilege check returned no row")
    return bool(row[0])


def _validate_role_name(role_name: str) -> None:
    if not role_name.strip():
        raise GroundingBrokerProvisioningError("broker role name must not be empty")
    if "\x00" in role_name:
        raise GroundingBrokerProvisioningError("broker role name must not contain NUL")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Provision the restricted PostgreSQL role for Engram grounding broker runs.",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("ENGRAM_DATABASE_URL", DEFAULT_DATABASE_URL),
        help="administrator/operator DSN for the already-migrated Engram database",
    )
    parser.add_argument("--role", default=DEFAULT_BROKER_ROLE)
    parser.add_argument(
        "--password-env",
        default=DEFAULT_PASSWORD_ENV,
        help="environment variable containing the broker role password",
    )
    parser.add_argument(
        "--no-login",
        action="store_true",
        help="create/update the broker role as NOLOGIN for SET ROLE tests",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    password = os.environ.get(args.password_env)
    with psycopg.connect(args.database_url) as conn, conn.transaction():
        result = provision_grounding_broker_role(
            conn,
            role_name=args.role,
            login=not args.no_login,
            password=password,
            database_url_for_suggestion=args.database_url,
        )
    print(f"provisioned grounding broker role: {result.role_name}")
    print(f"login enabled: {str(result.login_enabled).lower()}")
    print(
        f"password configured from {args.password_env}: "
        f"{str(result.password_configured).lower()}"
    )
    print("set this for provider-backed materializer runs:")
    print(f"ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL={result.suggested_database_url}")
    if result.password_configured:
        print(
            "also provide the password through libpq environment variable PGPASSWORD "
            "or a service file"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
