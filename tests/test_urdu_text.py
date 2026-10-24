from app.utils.urdu_text import render_urdu


def test_empty_text_is_returned_unchanged() -> None:
    assert render_urdu("") == ""


def test_urdu_text_is_marked_right_to_left() -> None:
    rendered = render_urdu("سر درد")

    assert rendered.startswith("‏")
    assert len(rendered) > 1
