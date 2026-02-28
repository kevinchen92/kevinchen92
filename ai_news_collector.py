#!/usr/bin/env python3
"""Collect daily AI news from mainstream media RSS feeds."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Iterable


DEFAULT_FEEDS = [
    ("BBC Technology", "http://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("NYTimes Technology", "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"),
    ("The Guardian Technology", "https://www.theguardian.com/uk/technology/rss"),
    ("CNBC Technology", "https://www.cnbc.com/id/10001019/device/rss/rss.html"),
    ("Google News - AI", "https://news.google.com/rss/search?q=artificial+intelligence"),
]

AI_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "openai",
    "chatgpt",
    "gemini",
    "copilot",
    "llm",
    "anthropic",
    "deepmind",
    "机器学习",
    "人工智能",
    "大模型",
}


@dataclasses.dataclass(slots=True)
class NewsItem:
    source: str
    title: str
    link: str
    published: dt.datetime | None
    summary: str


def normalize_dt(value: dt.datetime, timezone: dt.tzinfo) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)


def parse_datetime(raw: str, timezone: dt.tzinfo) -> dt.datetime | None:
    raw = raw.strip()
    if not raw:
        return None

    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            parsed = dt.datetime.strptime(raw, fmt)
            if fmt.endswith("Z"):
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return normalize_dt(parsed, timezone)
        except ValueError:
            continue

    try:
        parsed = parsedate_to_datetime(raw)
        return normalize_dt(parsed, timezone)
    except (TypeError, ValueError):
        return None


def strip_xml_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def parse_feed(xml_text: str, source: str, timezone: dt.tzinfo) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    entries: list[NewsItem] = []

    for item in root.findall(".//item"):
        title = strip_xml_text(item.find("title"))
        link = strip_xml_text(item.find("link"))
        summary = strip_xml_text(item.find("description"))
        pub_raw = strip_xml_text(item.find("pubDate")) or strip_xml_text(item.find("published"))
        published = parse_datetime(pub_raw, timezone) if pub_raw else None
        if title and link:
            entries.append(NewsItem(source, title, link, published, summary))

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for item in root.findall(".//atom:entry", ns):
        title = strip_xml_text(item.find("atom:title", ns))
        summary = strip_xml_text(item.find("atom:summary", ns)) or strip_xml_text(item.find("atom:content", ns))
        published_raw = strip_xml_text(item.find("atom:published", ns)) or strip_xml_text(item.find("atom:updated", ns))

        link_node = item.find("atom:link[@rel='alternate']", ns) or item.find("atom:link", ns)
        link = ""
        if link_node is not None:
            link = link_node.attrib.get("href", "").strip()

        published = parse_datetime(published_raw, timezone) if published_raw else None
        if title and link:
            entries.append(NewsItem(source, title, link, published, summary))

    return entries


def is_ai_related(news: NewsItem) -> bool:
    text = f"{news.title} {news.summary}".lower()
    return any(keyword in text for keyword in AI_KEYWORDS)


def is_today(news: NewsItem, now: dt.datetime) -> bool:
    return news.published is not None and news.published.date() == now.date()


def collect_news(
    feeds: Iterable[tuple[str, str]],
    timezone: dt.tzinfo,
    timeout: int = 20,
) -> tuple[list[NewsItem], list[str]]:
    items: list[NewsItem] = []
    errors: list[str] = []

    for source, url in feeds:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "ai-news-collector/1.0 (+https://example.com)",
                    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            items.extend(parse_feed(body, source, timezone))
        except (urllib.error.URLError, ET.ParseError, TimeoutError) as exc:
            errors.append(f"[{source}] {url} -> {exc}")

    return items, errors


def render_markdown(now: dt.datetime, news_items: list[NewsItem], errors: list[str]) -> str:
    lines = [f"# 每日 AI 资讯 ({now:%Y-%m-%d})", ""]
    if news_items:
        grouped: dict[str, list[NewsItem]] = {}
        for item in news_items:
            grouped.setdefault(item.source, []).append(item)

        for source, entries in grouped.items():
            lines.append(f"## {source}")
            for entry in sorted(entries, key=lambda x: x.published or now, reverse=True):
                published_text = entry.published.strftime("%H:%M") if entry.published else "未知时间"
                lines.append(f"- [{entry.title}]({entry.link})（{published_text}）")
            lines.append("")
    else:
        lines.append("今天未抓取到符合 AI 关键词的新闻。")
        lines.append("")

    if errors:
        lines.append("## 抓取告警")
        for err in errors:
            lines.append(f"- {err}")
        lines.append("")

    return "\n".join(lines)


def save_output(markdown: str, news_items: list[NewsItem], output_prefix: str) -> None:
    md_path = f"{output_prefix}.md"
    json_path = f"{output_prefix}.json"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    payload = [
        {
            "source": i.source,
            "title": i.title,
            "link": i.link,
            "published": i.published.isoformat() if i.published else None,
            "summary": textwrap.shorten(i.summary, width=280, placeholder="..."),
        }
        for i in news_items
    ]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="抓取每日 AI 主流媒体资讯")
    p.add_argument(
        "--timezone-offset",
        type=int,
        default=8,
        help="时区偏移（小时），默认 +8",
    )
    p.add_argument(
        "--output-prefix",
        default="daily_ai_news",
        help="输出文件前缀，默认 daily_ai_news",
    )
    p.add_argument(
        "--include-all",
        action="store_true",
        help="包含今日全部新闻，不仅 AI 关键词",
    )
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    timezone = dt.timezone(dt.timedelta(hours=args.timezone_offset))
    now = dt.datetime.now(tz=timezone)

    items, errors = collect_news(DEFAULT_FEEDS, timezone)
    if not args.include_all:
        items = [i for i in items if is_ai_related(i)]
    items = [i for i in items if is_today(i, now)]
    items.sort(key=lambda x: x.published or now, reverse=True)

    markdown = render_markdown(now, items, errors)
    save_output(markdown, items, args.output_prefix)

    print(markdown)
    print(f"\n已输出: {args.output_prefix}.md, {args.output_prefix}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
