"""ASCII-fold Portuguese text for the game's ASCII-only UTF-8 text renderer."""

import unicodedata

MAP = {
    "\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00b2": "2",
    "\u00b3": "3", "\u00ba": "o", "\u00aa": "a", "\u20ac": "EUR",
}


def ascii_fold(text: str) -> str:
    text = "".join(MAP.get(ch, ch) for ch in text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.encode("ascii", "replace").decode("ascii")
    return text
