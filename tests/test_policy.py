from app.policy import blocked_term, clan_allowed


def test_blocked_term_is_case_insensitive():
    assert blocked_term("This contains BADWORD", ("badword",)) == "badword"
    assert blocked_term("normal message", ("badword",)) is None


def test_clan_allowlist_is_optional_but_strict_when_configured():
    assert clan_allowed("clan-a", ()) is True
    assert clan_allowed("clan-a", ("clan-a", "clan-b")) is True
    assert clan_allowed("clan-c", ("clan-a", "clan-b")) is False
