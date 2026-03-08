# Twitter → Binance Square Auto Sync

Automatically sync your tweets to Binance Square. Handles long tweets without truncation.

自动同步推文到币安广场，长推文不截断。

---

## Features / 功能

- **Long tweet support / 长推文支持** — Full text preserved, no truncation / 完整保留全文，不截断
- **Dual Twitter backend / 双数据源** — [6551.io](https://6551.io) and [xapi.to](https://xapi.to)
- **Smart filtering / 智能过滤** — Skips retweets, replies, and empty tweets / 跳过转推、回复、空推文
- **Deduplication / 去重** — SQLite-backed, never posts the same tweet twice / 基于 SQLite，不会重复发帖
- **Rate limiting / 限速** — Built-in rate limiter / 内置速率控制
- **Daily limit / 日限额** — Configurable daily post cap (default: 12) / 可配置每日发帖上限
- **Scheduled sync / 定时同步** — LaunchAgent (macOS) or cron (Linux)

## Twitter Data Sources / 推特数据源对比

| Feature / 特性 | 6551.io | xapi.to |
|---------|----------------------|---------|
| Long tweets / 长推文 | Native full text / 原生全文 | Requires extra GraphQL call / 需额外 GraphQL 调用 |
| Media URLs / 媒体链接 | Included in response / 响应中直接包含 | Requires extra GraphQL call / 需额外调用 |
| Query by / 查询方式 | Username / 用户名 | User ID / 用户 ID |
| Speed / 速度 | ~0.3s per sync / 每次 ~0.3 秒 | ~5s per sync / 每次 ~5 秒 |
| Setup / 注册 | Token from [6551.io/mcp](https://6551.io/mcp) | API key from [xapi.to](https://xapi.to) |

## Prerequisites / 前置条件

1. **Twitter API token / 推特 API 令牌** — Choose one / 二选一:
   - **6551.io**: Sign up at / 注册 [6551.io/mcp](https://6551.io/mcp)
   - **xapi.to**: Sign up at / 注册 [xapi.to](https://xapi.to)
2. **Binance Square Open API key / 币安广场 API 密钥** — Get it from / 获取方式: [Binance Square](https://www.binance.com/en/square) → Settings / 设置 → Open API
3. **Python 3.8+**

## Setup / 安装

```bash
git clone https://github.com/HertzCOMM/twitter-to-binance-square.git
cd twitter-to-binance-square

# Configure / 配置
cp config.example.json config.json
# Edit config.json with your API keys / 填入你的 API 密钥
```

### Configuration / 配置说明

Edit / 编辑 `config.json`:

```json
{
  "twitter": {
    "provider": "6551",
    "6551_token": "your-6551-token",
    "username": "your_twitter_handle",
    "xapi_key": "",
    "user_id": ""
  },
  "binance_square": {
    "api_key": "your-binance-square-openapi-key"
  },
  "sync": {
    "fetch_count": 20,
    "daily_post_limit": 12,
    "posts_per_run": 1,
    "max_text_length": 900
  }
}
```

**Using 6551.io:**
- Set `provider` to `"6551"` / 设置 `provider` 为 `"6551"`
- Fill in `6551_token` and `username` / 填入 `6551_token` 和 `username`

**Using xapi.to:**
- Set `provider` to `"xapi"` / 设置 `provider` 为 `"xapi"`
- Fill in `xapi_key` and `user_id` / 填入 `xapi_key` 和 `user_id`（推特数字用户 ID）

| Field / 字段 | Description / 说明 |
|-------|-------------|
| `provider` | `"6551"` or `"xapi"` / 数据源选择 |
| `6551_token` | Your 6551.io API token / 6551 API 令牌 |
| `username` | Twitter handle (without @) / 推特用户名（不带 @）|
| `xapi_key` | xapi.to API key (if using xapi) / xapi 密钥（选 xapi 时填）|
| `user_id` | Twitter numeric user ID (if using xapi) / 推特数字 ID（选 xapi 时填）|
| `fetch_count` | Tweets to fetch per run (default: 20) / 每次拉取推文数 |
| `daily_post_limit` | Max posts per day (default: 12) / 每日发帖上限 |
| `posts_per_run` | Posts per sync run (default: 1) / 每次同步发帖数 |
| `max_text_length` | Max text length before truncation (default: 900) / 截断字数上限 |

## Usage / 使用方法

```bash
# Preview / 预览（不真正发帖）
python3 sync.py --dry-run

# Post 1 tweet to Binance Square / 同步 1 条推文到币安广场
python3 sync.py

# Check sync status / 查看同步状态
python3 sync.py --status

# Reset / 重置（从头拉取，已发过的会跳过）
python3 sync.py --reset
```

## Schedule / 定时同步（每 2 小时）

### macOS (LaunchAgent)

```bash
chmod +x setup_schedule.sh
./setup_schedule.sh
```

### Linux (cron)

```bash
crontab -e
# Add / 添加:
0 */2 * * * cd /path/to/twitter-to-binance-square && python3 sync.py >> ~/.twitter-bsq-sync/sync.log 2>&1
```

## How it works / 工作原理

```
LaunchAgent / cron (every 2h / 每 2 小时)
    ↓
sync.py
    ├─ fetch_tweets()         ← 6551.io or xapi.to
    ├─ filter.should_sync()   ← skip retweets, replies / 过滤转推、回复
    ├─ enrich_tweet()         ← full long tweet text / 获取长推文全文
    ├─ filter.prepare_text()  ← clean & truncate / 清理并截断
    ├─ publisher.publish()    ← post to Binance Square / 发帖到币安广场
    └─ db.mark_posted()       ← record in SQLite / 记录已发
```

## Limitations / 已知限制

- **Text only / 仅支持文字** — Binance Square Open API does not support image uploads / 币安广场 API 不支持图片上传
- **No delete API / 无删帖接口** — Cannot programmatically delete BSQ posts / 无法通过 API 删除帖子

## License

MIT
