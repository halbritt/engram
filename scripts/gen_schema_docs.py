#!/usr/bin/env python3
"""Generate Mermaid ER diagram and schema reference from the live engram database."""

import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

DB_URL = os.environ.get("ENGRAM_DATABASE_URL", "postgresql:///engram")
OUT_DIR = Path(__file__).parent.parent / "docs" / "schema"
EXCLUDE_TABLES = {"schema_migrations"}

MERMAID_TYPE_MAP = {
    "uuid": "UUID",
    "text": "TEXT",
    "integer": "INT",
    "bigint": "BIGINT",
    "boolean": "BOOLEAN",
    "timestamp with time zone": "TIMESTAMPTZ",
    "timestamp without time zone": "TIMESTAMP",
    "jsonb": "JSONB",
    "json": "JSON",
    "USER-DEFINED": "ENUM",
    "ARRAY": "ARRAY",
    "smallint": "SMALLINT",
    "numeric": "NUMERIC",
    "double precision": "FLOAT",
}


def fetch_tables(conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        return [r["table_name"] for r in cur if r["table_name"] not in EXCLUDE_TABLES]


def fetch_columns(conn, table):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                column_name,
                data_type,
                udt_name,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        return list(cur)


def fetch_fkeys(conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                tc.table_name AS from_table,
                kcu.column_name AS from_col,
                ccu.table_name AS to_table,
                ccu.column_name AS to_col,
                tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
            ORDER BY from_table, from_col
        """)
        return list(cur)


def fetch_pkeys(conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                tc.table_name,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
        """)
        pkeys = {}
        for r in cur:
            pkeys.setdefault(r["table_name"], set()).add(r["column_name"])
        return pkeys


def col_type_label(col):
    dt = col["data_type"]
    if dt == "USER-DEFINED":
        return col["udt_name"].upper()
    if dt == "ARRAY":
        return col["udt_name"].lstrip("_").upper() + "[]"
    return MERMAID_TYPE_MAP.get(dt, dt.upper())


def build_mermaid(tables, columns_by_table, fkeys, pkeys):
    lines = ["erDiagram"]
    for table in tables:
        lines.append(f"    {table} {{")
        for col in columns_by_table[table]:
            pk_marker = " PK" if col["column_name"] in pkeys.get(table, set()) else ""
            null_marker = "" if col["is_nullable"] == "YES" else ""
            type_label = col_type_label(col)
            lines.append(f"        {type_label} {col['column_name']}{pk_marker}")
        lines.append("    }")

    seen = set()
    for fk in fkeys:
        if fk["from_table"] in EXCLUDE_TABLES or fk["to_table"] in EXCLUDE_TABLES:
            continue
        key = (fk["from_table"], fk["to_table"], fk["from_col"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(
            f'    {fk["from_table"]} }}o--|| {fk["to_table"]} : "{fk["from_col"]}"'
        )

    return "\n".join(lines)


def build_table_md(table, columns, pkey_cols):
    lines = [f"## {table}\n", "| Column | Type | Nullable | Default |", "|--------|------|----------|---------|"]
    for col in columns:
        pk = " **PK**" if col["column_name"] in pkey_cols else ""
        nullable = "YES" if col["is_nullable"] == "YES" else "NO"
        default = col["column_default"] or ""
        if len(default) > 40:
            default = default[:37] + "..."
        lines.append(f"| `{col['column_name']}`{pk} | `{col_type_label(col)}` | {nullable} | `{default}` |")
    return "\n".join(lines)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(DB_URL) as conn:
        tables = fetch_tables(conn)
        columns_by_table = {t: fetch_columns(conn, t) for t in tables}
        fkeys = fetch_fkeys(conn)
        pkeys = fetch_pkeys(conn)

    mermaid = build_mermaid(tables, columns_by_table, fkeys, pkeys)

    # Main schema README with ER diagram
    readme_lines = [
        "# Engram Schema",
        "",
        "> Auto-generated by `make schema-docs`. Do not edit by hand.",
        "",
        "## Entity-Relationship Diagram",
        "",
        "```mermaid",
        mermaid,
        "```",
        "",
        "## Tables",
        "",
    ]
    for table in tables:
        pkey_cols = pkeys.get(table, set())
        readme_lines.append(build_table_md(table, columns_by_table[table], pkey_cols))
        readme_lines.append("")

    (OUT_DIR / "README.md").write_text("\n".join(readme_lines))
    print(f"wrote {OUT_DIR / 'README.md'}")


if __name__ == "__main__":
    main()
