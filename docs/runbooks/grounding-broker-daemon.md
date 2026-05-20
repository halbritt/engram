# Grounding Broker Daemon

`engram entity-grounding broker-daemon` is the local long-running workflow for
approved RFC 0055 entity-grounding grants. It repeatedly runs the approved-grant
materializer under the restricted broker database role.

This process is network-capable when a provider such as Tavily is configured.
Approved entity search strings may include private text; treat the daemon
environment, broker DSN, provider key, and logs as sensitive.

## Prerequisites

1. Apply migrations.
2. Provision and check the restricted broker role:

```sh
make provision-grounding-broker
make check-grounding-broker
```

3. Configure the broker DSN outside the repo. Prefer local libpq config such as
   `~/.pgpass` or a user service environment file rather than committing
   credentials:

```sh
export ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL='postgresql://engram_grounding_broker@localhost/engram'
```

4. Configure the optional provider. For Tavily, the provider remains disabled
   until both variables are set:

```sh
export ENGRAM_CLAIM_GROUNDING_SEARCH_PROVIDER=tavily
export ENGRAM_CLAIM_GROUNDING_TAVILY_API_KEY='set-outside-shell-history'
```

## Smoke Run

Run one bounded polling iteration before starting a long-lived process:

```sh
engram entity-grounding broker-daemon --tenant personal --corpus personal --max-iterations 1
```

The command refuses to start unless
`ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` is set. Output is sanitized JSON
and redacts secret-shaped fields.

## Long-Running Run

The Makefile target wraps the same command:

```sh
ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL='postgresql://engram_grounding_broker@localhost/engram' \
make grounding-broker-daemon
```

Tunables:

```sh
GROUNDING_BROKER_TENANT=personal
GROUNDING_BROKER_CORPUS=personal
GROUNDING_BROKER_DAEMON_LIMIT=20
GROUNDING_BROKER_DAEMON_INTERVAL=10
```

Direct CLI equivalent:

```sh
engram entity-grounding broker-daemon \
  --tenant personal \
  --corpus personal \
  --limit 20 \
  --interval 10
```

For a user-level service, keep the service file and environment file outside
the repo and run the command above as a local user with only the broker DSN and
provider key it needs. Do not run the daemon with a normal corpus-reading
`ENGRAM_DATABASE_URL`.

## Safety Invariants

- `engram entity-grounding draft` remains corpus-reading and network-free; do
  not run it under the broker role.
- `broker-daemon` must run with the restricted
  `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL`.
- Each polling iteration uses a PostgreSQL transaction advisory lock so two
  daemon instances do not process the same batch concurrently.
- Grants with an existing prepared, dispatched, succeeded, or failed network
  dispatch row are not selected again. Retrying a provider call requires a new
  approved grant, not an automatic tight loop.
- Provider result rows are still re-filtered by the materializer before local
  evidence insertion.
- Broker-readable request/grant sidecars are sensitive metadata because they
  include entity surface strings and approved search queries.
