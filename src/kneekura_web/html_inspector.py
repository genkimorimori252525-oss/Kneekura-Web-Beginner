"""Structure observations without executing website scripts."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin

from .policy import TargetRejected, normalize_target, same_host


class _Inspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.headings: list[dict] = []
        self.links: list[dict] = []
        self.images: list[dict] = []
        self.stylesheets: list[str] = []
        self.scripts: list[str] = []
        self.forms: list[dict] = []
        self.text: list[str] = []
        self._heading: str | None = None
        self._in_title = False
        self._skip = 0
        self._in_head = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "head":
            self._in_head += 1
        if tag in ("script", "style", "noscript", "svg"):
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append({"level": int(tag[1]), "text": ""})
            self._heading = tag
        if tag == "meta" and (attr.get("name") or "").lower() == "description":
            self.description = attr.get("content") or ""
        if tag == "a" and attr.get("href"):
            self.links.append({"href": attr["href"], "text": (attr.get("aria-label") or "").strip()})
        if tag == "img" and attr.get("src"):
            self.images.append({"src": attr["src"], "alt": attr.get("alt") or ""})
        if tag == "link" and "stylesheet" in (attr.get("rel") or "").lower().split():
            if attr.get("href"):
                self.stylesheets.append(attr["href"])
        if tag == "script" and attr.get("src"):
            self.scripts.append(attr["src"])
        if tag == "form":
            self.forms.append({
                "method": (attr.get("method") or "GET").upper(),
                "action": attr.get("action") or "",
            })

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            self._in_head = max(0, self._in_head - 1)
        if tag in ("script", "style", "noscript", "svg"):
            self._skip = max(0, self._skip - 1)
        if tag == "title":
            self._in_title = False
        if tag == self._heading:
            self._heading = None

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self._in_title:
            self.title += (" " if self.title else "") + cleaned
        if self._heading and self.headings:
            self.headings[-1]["text"] += (
                (" " if self.headings[-1]["text"] else "") + cleaned
            )
        if not self._skip and not self._in_head:
            self.text.append(cleaned)


def inspect_html(html: str) -> dict:
    parser = _Inspector()
    parser.feed(html)
    parser.close()
    return {
        "title": parser.title,
        "description": parser.description,
        "headings": parser.headings,
        "links": parser.links,
        "images": parser.images,
        "stylesheets": list(dict.fromkeys(parser.stylesheets)),
        "scripts": list(dict.fromkeys(parser.scripts)),
        "forms": parser.forms,
        "text_excerpt": " ".join(parser.text)[:6000],
    }


def in_scope_links(base_url: str, html_links: list[dict], origin: str) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for link in html_links:
        try:
            candidate = normalize_target(urldefrag(urljoin(base_url, link.get("href", "")))[0])
        except (TargetRejected, ValueError):
            continue
        if same_host(candidate, origin) and candidate not in seen:
            seen.add(candidate)
            results.append(candidate)
    return results
