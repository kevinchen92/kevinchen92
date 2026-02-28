# 每日 AI 资讯收集器

这是一个轻量 Python 程序，用于每天自动抓取**主流媒体**的 AI 相关资讯，并输出：

- `daily_ai_news.md`（给人阅读）
- `daily_ai_news.json`（便于后续接入数据库或机器人）

## 功能特点

- 抓取多个 RSS/Atom 媒体源（BBC、NYTimes、Guardian、CNBC、Google News AI）
- 仅保留“今天”的新闻（按时区）
- 默认按 AI 关键词过滤（可切换为“今日全部科技资讯”）
- 同时输出 Markdown 与 JSON
- 抓取失败源会在报告中展示告警

## 使用方式

```bash
python ai_news_collector.py
```

### 常用参数

```bash
python ai_news_collector.py --timezone-offset 8 --output-prefix reports/ai_news_$(date +%F)
```

- `--timezone-offset`：时区偏移小时，默认 `8`（北京时间）
- `--output-prefix`：输出文件前缀，默认 `daily_ai_news`
- `--include-all`：不过滤 AI 关键词，输出今日全部抓到的新闻

## 自动化（Linux/macOS cron）

每天早上 8:30 自动运行：

```cron
30 8 * * * cd /workspace/kevinchen92 && /usr/bin/python3 ai_news_collector.py --timezone-offset 8 --output-prefix reports/ai_news_$(date +\%F) >> logs/ai_news.log 2>&1
```

建议先创建目录：

```bash
mkdir -p reports logs
```

## 二次开发建议

- 新增数据源：在 `DEFAULT_FEEDS` 中增加 `(媒体名, feed_url)`
- 调整 AI 判断规则：修改 `AI_KEYWORDS`
- 接入企业微信/钉钉/Slack：读取生成的 `json` 后推送
