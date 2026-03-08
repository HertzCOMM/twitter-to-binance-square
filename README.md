# Twitter → Binance Square Auto Sync

Automatically sync your tweets to Binance Square. Handles long tweets (note_tweet) without truncation.

## Features

- **Long tweet support** — Fetches full text via Twitter GraphQL API, no more truncated posts
- **Smart filtering** — Skips retweets, replies, and media-only tweets
- **Deduplication** — SQLite-backed, never posts the same tweet twice
- **Rate limiting** — Built-in rate limiter for Twitter API calls
- **Daily limit** — Configurable daily post cap (default: 12)
- **Scheduled sync** — LaunchAgent (macOS) or cron (Linux), posts 1 tweet per run

## Prerequisites

1. **xapi.to account** — Sign up at [xapi.to](https://xapi.to) and get an API key
2. **Binance Square Open API key** — Get it from [Binance Square settings](https://www.binance.com/en/square) → Open API
3. **Python 3.8+**
4. **curl** (for GraphQL tweet detail fetching)

## Setup

```bash
git clone https://github.com/hertzbot-v/twitter-to-binance-square.git
cd twitter-to-binance-square

# Configure
cp config.example.json config.json
# Edit config.json with your API keys and Twitter user ID
```

### Find your Twitter user ID

If you don't know your Twitter user ID, you can find it at [tweeterid.com](https://tweeterid.com) or run:

```bash
python3 -c "
import xapi_client as xapi
import json
cfg = json.load(open('config.json'))
uid = xapi.execute(cfg['twitter']['xapi_key'], 'twitter.user_by_screen_name', {'screen_name': 'YOUR_HANDLE'})
print('User ID:', uid.get('rest_id'))
"
```

## Usage

```bash
# Preview what would be posted (no actual posting)
python3 sync.py --dry-run

# Post 1 tweet to Binance Square
python3 sync.py

# Check sync status
python3 sync.py --status

# Reset cursor (re-fetch all tweets, skips already-posted ones)
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
# Add this line (adjust path):
0 */2 * * * cd /path/to/twitter-to-binance-square && python3 sync.py >> ~/.twitter-bsq-sync/sync.log 2>&1
```

## Configuration

Edit `config.json`:

| Field | Description |
|-------|-------------|
| `twitter.xapi_key` | Your xapi.to API key |
| `twitter.user_id` | Your Twitter numeric user ID |
| `binance_square.api_key` | Your Binance Square Open API key |
| `sync.fetch_count` | Tweets to fetch per run (default: 20) |
| `sync.daily_post_limit` | Max posts per day (default: 12) |
| `sync.posts_per_run` | Posts per run (default: 1) |
| `sync.max_text_length` | Max text length before truncation (default: 900) |

## Limitations

- **Text only** — Binance Square Open API does not support image uploads. Tweet images are not synced.
- **No delete API** — Cannot programmatically delete posts from Binance Square.
- **Rate limits** — xapi.to free tier has usage limits. For high-volume accounts, consider upgrading.

## How it works

```
LaunchAgent / cron (every 2h)
    ↓
sync.py
    ├─ xapi_client.get_user_tweets()     ← fetch recent tweets
    ├─ filter.should_sync()              ← skip retweets, replies, etc.
    ├─ xapi_client.get_tweet_detail()    ← get full long tweet text
    ├─ filter.prepare_text()             ← clean & truncate
    ├─ publisher.publish()               ← post to Binance Square
    └─ db.mark_posted()                  ← record in SQLite
```

## License

MIT
