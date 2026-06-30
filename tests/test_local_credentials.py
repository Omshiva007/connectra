"""Tests for local User app credentials and session state."""


def test_mailbox_key_round_trip_and_session(isolated_data_dir):
    from connectra_core.local_credentials import (
        clear_session,
        load_mailbox_key,
        load_session,
        save_mailbox_key,
        save_session,
    )

    save_mailbox_key("user@example.com", "four word app key")
    save_session("user@example.com")

    assert load_mailbox_key("user@example.com") == "four word app key"
    assert load_mailbox_key("other@example.com") is None
    assert load_session() == "user@example.com"

    clear_session()

    assert load_session() is None
