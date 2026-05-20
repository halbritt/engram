from __future__ import annotations

from scripts.provision_grounding_broker_role import suggest_broker_database_url


def test_suggest_broker_database_url_preserves_local_socket_url() -> None:
    assert (
        suggest_broker_database_url(
            "postgresql:///engram",
            role_name="engram_grounding_broker",
        )
        == "postgresql:///engram?user=engram_grounding_broker"
    )


def test_suggest_broker_database_url_replaces_network_user_without_password() -> None:
    assert (
        suggest_broker_database_url(
            "postgresql://admin:secret@127.0.0.1:5432/engram?sslmode=disable",
            role_name="engram_grounding_broker",
        )
        == "postgresql://engram_grounding_broker@127.0.0.1:5432/engram?sslmode=disable"
    )
