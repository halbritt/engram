# Grounding Broker PostgreSQL Role

This runbook provisions the restricted database role used by
`engram entity-grounding process-approved` and
`engram entity-grounding broker-daemon` when a network provider is enabled. It
keeps the network-capable materializer out of normal Engram DB authority.

## Provision

Run after `make migrate` has applied migrations 023 and 024:

```sh
make provision-grounding-broker
```

By default this provisions role `engram_grounding_broker` against
`postgresql:///engram`. Override as needed:

```sh
GROUNDING_BROKER_DATABASE_URL=postgresql:///engram \
GROUNDING_BROKER_ROLE=engram_grounding_broker \
ENGRAM_GROUNDING_BROKER_PASSWORD='set-this-outside-shell-history' \
make provision-grounding-broker
```

The script prints a password-free
`ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` suggestion. If the role uses a
password, pass it through libpq configuration such as `PGPASSWORD` or a local
service file rather than committing it to the repo.

## Check

Verify the role grants through an operator connection:

```sh
make check-grounding-broker
```

After setting `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL`, the same script can
also check the actual broker login path:

```sh
ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL='postgresql://engram_grounding_broker@localhost/engram' \
PGPASSWORD='set-this-outside-shell-history' \
.venv/bin/python scripts/check_grounding_broker_role.py
```

The check confirms the broker can read only minimized request/grant/audit
sidecars, can append the dispatch/response/link/evidence/action rows needed by
the materializer, and cannot read or mutate raw corpus tables.

## Runtime

Use the broker DSN only for the network-capable approved-grant materializer and
daemon workflow:

```sh
ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL='postgresql:///engram?user=engram_grounding_broker' \
engram entity-grounding process-approved --tenant personal --corpus personal --limit 20

ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL='postgresql://engram_grounding_broker@localhost/engram' \
engram entity-grounding broker-daemon --tenant personal --corpus personal --max-iterations 1
```

`engram entity-grounding draft` remains corpus-reading and network-free. It
should not use the broker role.

For long-running daemon operation, see
`docs/runbooks/grounding-broker-daemon.md`.
