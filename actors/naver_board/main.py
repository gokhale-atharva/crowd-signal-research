"""Runs on Apify, never as a local fallback around the required collection provider."""

import asyncio
import re
from datetime import UTC, datetime
from urllib.parse import parse_qs, urljoin, urlparse
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

BASE = "https://finance.naver.com"


def parse_post(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.select_one(".view .title, .view .c.p15, .view .p15, h3")
    body = soup.select_one("#body, .view .view_se, .view .content")
    text = body.get_text(" ", strip=True) if body else ""
    if not text:
        raise ValueError("Naver discussion post body is unavailable; selectors may have changed")
    match = re.search(
        r"(20\d{2})[.\-/](\d{2})[.\-/](\d{2})\s+(\d{2}):(\d{2})", soup.get_text(" ", strip=True)
    )
    if not match:
        raise ValueError("Naver post timestamp is unavailable")
    timestamp = datetime(*map(int, match.groups()), tzinfo=ZoneInfo("Asia/Seoul"))
    author = soup.select_one(".view .gray03, .view .writer")
    return {
        "url": url,
        "text": text,
        "title": heading.get_text(" ", strip=True) if heading else None,
        "timestamp": timestamp.isoformat(),
        "author": author.get_text(" ", strip=True) if author else None,
        "likes": None,
        "reposts": None,
        "views": None,
        "author_followers": None,
    }


async def main() -> None:
    from apify import Actor

    async with Actor:
        request = await Actor.get_input() or {}
        ticker = str(request.get("ticker", ""))
        if not re.fullmatch(r"\d{6}", ticker):
            raise ValueError("ticker must contain six digits")
        limit = min(20, max(1, int(request.get("maxItems", 20))))
        pages = min(5, max(1, int(request.get("maxPages", 3))))
        cutoff = datetime.fromisoformat(request["dateFrom"].replace("Z", "+00:00"))
        if cutoff.tzinfo is None:
            raise ValueError("dateFrom must include a timezone")
        seen, emitted = set(), 0
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "CrowdSignalResearch/0.1 (bounded public-board research)"},
        ) as client:
            robots = await client.get(BASE + "/robots.txt")
            if robots.status_code == 200:
                from urllib.robotparser import RobotFileParser

                parser = RobotFileParser()
                parser.parse(robots.text.splitlines())
                if not parser.can_fetch("CrowdSignalResearch", BASE + "/item/board.naver"):
                    raise ValueError(
                        "robots.txt disallows this crawler; select another permitted source"
                    )
            for page in range(1, pages + 1):
                listing = await client.get(
                    BASE + "/item/board.naver", params={"code": ticker, "page": page}
                )
                listing.raise_for_status()
                soup = BeautifulSoup(listing.content, "html.parser", from_encoding="euc-kr")
                urls = []
                for anchor in soup.select('a[href*="board_read"]'):
                    url = urljoin(BASE, anchor.get("href", ""))
                    parsed = urlparse(url)
                    if (
                        parsed.netloc == "finance.naver.com"
                        and parse_qs(parsed.query).get("code") == [ticker]
                        and url not in seen
                    ):
                        seen.add(url)
                        urls.append(url)
                if not urls:
                    Actor.log.warning(
                        "No discussion links found; endpoint or selectors may have changed"
                    )
                    break
                for url in urls:
                    response = await client.get(url)
                    response.raise_for_status()
                    response.encoding = "euc-kr"
                    record = parse_post(response.text, url)
                    stamp = datetime.fromisoformat(record["timestamp"])
                    if stamp < cutoff:
                        continue
                    record["ticker"] = ticker
                    record["observed_at"] = datetime.now(UTC).isoformat()
                    await Actor.push_data(record)
                    emitted += 1
                    if emitted >= limit:
                        return
                    await asyncio.sleep(0.6)
        Actor.log.info("Emitted %s discussion posts", emitted)


if __name__ == "__main__":
    asyncio.run(main())
