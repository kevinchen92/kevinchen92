import datetime as dt

from ai_news_collector import is_ai_related, parse_feed


def test_parse_feed_rss_item():
    xml = """<?xml version='1.0'?>
    <rss><channel>
      <item>
        <title>AI startup raises funding</title>
        <link>https://example.com/1</link>
        <description>OpenAI and LLM tools are growing fast.</description>
        <pubDate>Fri, 28 Feb 2025 08:30:00 +0000</pubDate>
      </item>
    </channel></rss>
    """
    tz = dt.timezone(dt.timedelta(hours=8))
    items = parse_feed(xml, "Example", tz)
    assert len(items) == 1
    assert items[0].title == "AI startup raises funding"
    assert items[0].published is not None


def test_ai_keyword_filter():
    xml = """<?xml version='1.0'?>
    <rss><channel>
      <item>
        <title>Cloud vendor introduces chatbot copilot</title>
        <link>https://example.com/2</link>
        <description>new service</description>
        <pubDate>Fri, 28 Feb 2025 08:30:00 +0000</pubDate>
      </item>
      <item>
        <title>Basketball finals scores</title>
        <link>https://example.com/3</link>
        <description>sports update</description>
        <pubDate>Fri, 28 Feb 2025 08:30:00 +0000</pubDate>
      </item>
    </channel></rss>
    """
    tz = dt.timezone.utc
    items = parse_feed(xml, "Example", tz)
    assert is_ai_related(items[0]) is True
    assert is_ai_related(items[1]) is False
