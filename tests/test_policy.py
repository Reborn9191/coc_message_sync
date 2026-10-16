from app.policy import blocked_term


def test_blocked_term_is_case_insensitive():
    assert blocked_term("This contains BADWORD", ("badword",)) == "badword"
    assert blocked_term("normal message", ("badword",)) is None
