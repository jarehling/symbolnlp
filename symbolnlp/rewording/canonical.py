"""Conservative surface normalization, independent of semantic rewriting."""
from dataclasses import dataclass
import unicodedata


@dataclass(frozen=True)
class Canonicalized:
    text: str
    changes: tuple[str, ...]


def canonicalize(text: str) -> Canonicalized:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Text must be a nonempty string")
    changes = []
    normalized = unicodedata.normalize('NFKC', text)
    if normalized != text:
        changes.append('unicode_nfkc')
    # Reject rather than silently erase non-whitespace control/format marks.
    # Deleting a zero-width mark can join words and change the lexical content.
    if any(unicodedata.category(c).startswith('C') and not c.isspace() for c in normalized):
        raise ValueError("Control/format characters require explicit review; not silently removed")
    whitespace = ' '.join(normalized.split())
    if whitespace != normalized:
        changes.append('whitespace')
    return Canonicalized(whitespace, tuple(changes))
