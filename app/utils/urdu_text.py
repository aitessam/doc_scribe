from __future__ import annotations

from typing import Final

import arabic_reshaper
from bidi.algorithm import get_display

_RTL_MARK: Final[str] = "\u200f"


def render_urdu(text: str) -> str:
    """Return text rendered for right-to-left Urdu display.

    This applies Arabic reshaping and bidirectional reordering so that Urdu
    strings display correctly in left-to-right UI components such as Streamlit.

    Args:
        text: Raw Urdu or mixed Urdu/English text.

    Returns:
        str: Text transformed for proper RTL display.
    """

    if not text:
        return text

    # Reshape Arabic-script characters, then apply bidi algorithm.
    reshaped = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped)
    return f"{_RTL_MARK}{bidi_text}"
