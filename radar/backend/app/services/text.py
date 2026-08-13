import html
import re
from html.parser import HTMLParser


_WHITESPACE = re.compile(r"\s+")
_NON_WORD = re.compile(r"[\W_]+", re.UNICODE)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def normalize_space(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE.sub(" ", value).strip()


def normalize_for_match(value: str | None) -> str:
    if not value:
        return ""
    return normalize_space(_NON_WORD.sub(" ", value)).casefold()


def html_to_text(value: str | None) -> str | None:
    if not value:
        return None
    decoded = html.unescape(html.unescape(value))
    parser = _TextExtractor()
    parser.feed(decoded)
    parser.close()
    text = normalize_space(" ".join(parser.parts))
    return text or None
