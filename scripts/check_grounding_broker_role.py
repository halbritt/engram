from __future__ import annotations

import argparse
import os

import psycopg
from provision_grounding_broker_role import (
    BROKER_INSERT_TABLES,
    BROKER_SELECT_TABLES,
    DEFAULT_BROKER_ROLE,
    DEFAULT_DATABASE_URL,
    RAW_CORPUS_TABLES,
)


class GroundingBrokerCheckError(RuntimeError):
    """Raised when the configured broker DSN does not match the contract."""


def check_grounding_broker_role(conn: psycopg.Connection) -> None:
    """Validate that the current connection has the expected restricted rights."""
    check_grounding_broker_role_name(conn, role_name=_current_user(conn))


def check_grounding_broker_role_name(conn: psycopg.Connection, *, role_name: str) -> None:
    """Validate expected restricted rights for a named role."""
    for table_name in BROKER_SELECT_TABLES:
        _assert_privilege(conn, role_name, table_name, "SELECT", expected=True)
    for table_name in BROKER_INSERT_TABLES:
        _assert_privilege(conn, role_name, table_name, "INSERT", expected=True)
        _assert_privilege(conn, role_name, table_name, "UPDATE", expected=False)
        _assert_privilege(conn, role_name, table_name, "DELETE", expected=False)
    for table_name in RAW_CORPUS_TABLES:
        _assert_privilege(conn, role_name, table_name, "SELECT", expected=False)
        _assert_privilege(conn, role_name, table_name, "INSERT", expected=False)


def _current_user(conn: psycopg.Connection) -> str:
    row = conn.execute("SELECT current_user").fetchone()
    if row is None:
        raise GroundingBrokerCheckError("current_user check returned no row")
    return str(row[0])


def _assert_privilege(
    conn: psycopg.Connection,
    role_name: str,
    table_name: str,
    privilege: str,
    *,
    expected: bool,
) -> None:
    row = conn.execute(
        "SELECT has_table_privilege(%s, %s, %s)",
        (role_name, f"public.{table_name}", privilege),
    ).fetchone()
    if row is None:
        raise GroundingBrokerCheckError("privilege check returned no row")
    observed = bool(row[0])
    if observed != expected:
        state = "has" if observed else "does not have"
        expected_state = "have" if expected else "not have"
        raise GroundingBrokerCheckError(
            f"{role_name} {state} {privilege} on public.{table_name}; "
            f"expected to {expected_state} it"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check the configured Engram grounding broker PostgreSQL role.",
    )
    parser.add_argument(
        "--broker-database-url",
        default=os.environ.get("ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL", ""),
        help=(
            "broker DSN; defaults to ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL. "
            "When unset, the check uses --database-url to inspect --role privileges."
        ),
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("ENGRAM_DATABASE_URL", DEFAULT_DATABASE_URL),
        help="operator DSN used for role privilege checks when --broker-database-url is unset",
    )
    parser.add_argument(
        "--role",
        default=DEFAULT_BROKER_ROLE,
        help="broker role used for privilege checks when --broker-database-url is unset",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.broker_database_url:
        with psycopg.connect(args.broker_database_url) as conn:
            check_grounding_broker_role(conn)
        print("grounding broker role privilege check passed")
        return 0
    with psycopg.connect(args.database_url) as conn:
        check_grounding_broker_role_name(conn, role_name=args.role)
    print("grounding broker role privilege check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
