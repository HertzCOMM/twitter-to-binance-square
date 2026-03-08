# Twitter → Binance Square Auto Sync

Automatically sync your tweets to Binance Square. Handles long tweets without truncation.

## Features

- **Long tweet support** — Full text preserved, no truncation
- **Dual Twitter backend** — Supports [6551.io](https://6551.io) (recommended) and [xapi.to](https://xapi.to)
- **Smart filtering** — Skips retweets, replies, and empty tweets
- **Deduplication** — SQLite-backed, never posts the same tweet twice
- **Rate limiting** — Built-in rate limiter for Twitter API calls
- **Daily limit** — Configurable daily post cap (default: 12)
- **Scheduled sync** — LaunchAgent (macOS) or cron (Linux)

## Twitter Data Sources

| Feature | 6551.io (recommended) | xapi.to |
|---------|----------------------|---------|
| Long tweets | Native full text | Requires extra GraphQL call |
| Media URLs | Included in response | Requires extra GraphQL call |
| Query by | Username | User ID |
| Speed | ~0.3s per sync | ~5s per sync |
| Setup | Token from [6551.io/mcp](https://6551.io/mcp) | API key from [xapi.to](https://xapi.to) |

## Prerequisites

1. **Twitter API token** — Choose one:
   - **6551.io** (recommended): Sign up at [6551.io/mcp](https://6551.io/mcp)
   - **xapi.to**: Sign up at [xapi.to](https://xapi.to)
2. **Binance Square Open API key** — Get it from [Binance Square](https://www.binance.com/en/square) → Settings → Open API
3. **Python 3.8+**

## Setup

```bash
git clone https://github.com/HertzCOMM/twitter-to-binance-square.git
cd twitter-to-binance-square

# Configure
cp config.example.json config.json
# Edit config.json with your API keys
```

### Configuration

Edit `config.json`:

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

**Using 6551.io (recommended):**
- Set `provider` to `"6551"`
- Fill in `6551_token` and `username`

**Using xapi.to:**
- Set `provider` to `"xapi"`
- Fill in `xapi_key` and `user_id` (numeric Twitter user ID)

| Field | Description |
|-------|-------------|
| `provider` | `"6551"` or `"xapi"` |
| `6551_token` | Your 6551.io API token |
| `username` | Your Twitter handle (without @) |
| `xapi_key` | Your xapi.to API key (if using xapi) |
| `user_id` | Your Twitter numeric user ID (if using xapi) |
| `fetch_count` | Tweets to fetch per run (default: 20) |
| `daily_post_limit` | Max posts per day (default: 12) |
| `posts_per_run` | Posts per sync run (default: 1) |
| `max_text_length` | Max text length before truncation (default: 900) |

## Usage

```bash
# Preview what would be posted (no actual posting)
python3 sync.py --dry-run

# Post 1 tweet to Binance Square
python3 sync.py

# Check sync status
python3 sync.py --status

# Reset (re-fetch all tweets, skips already-posted ones)
python3 sync.py --reset
```

## Schedule (auto-sync every 2 hours)

### macOS (LaunchAgent)

```bash
chmod +x setup_schedule.sh
./setup_schedule.sh
```

### Linux (cron)

```bash
crontab -e
# Add:
0 */2 * * * cd /path/to/twitter-to-binance-square && python3 sync.py >> ~/.twitter-bsq-sync/sync.log 2>&1
```

## How it works

```
LaunchAgent / cron (every 2h)
    ↓
sync.py
    ├─ fetch_tweets()         ← 6551.io or xapi.to
    ├─ filter.should_sync()   ← skip retweets, replies, etc.
    ├─ enrich_tweet()         ← full long tweet text + media
    ├─ filter.prepare_text()  ← clean & truncate for BSQ
    ├─ publisher.publish()    ← post to Binance Square
    └─ db.mark_posted()      ← record in SQLite
```

## Limitations

- **Text only** — Binance Square Open API does not support image uploads
- **No delete API** — Cannot programmatically delete BSQ posts

## License

MIT
