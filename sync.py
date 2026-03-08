"""
Twitter → Binance Square Sync

Syncs your tweets to Binance Square automatically.
- Supports two Twitter data sources: 6551.io (recommended) and xapi.to
- Handles long tweets (note_tweet) without truncation
- Deduplicates via SQLite
- Rate-limited API calls

Usage:
  python sync.py              # Sync once (post 1 oldest unposted tweet)
  python sync.py --dry-run    # Preview what would be posted
  python sync.py --reset      # Clear cursor (re-fetch from beginning)
  python sync.py --status     # View sync statistics
"""
from __future__ import annotations

import sys
import time
import json
import argparse
from pathlib import Path

import db
import filter as fil
import publisher as pub

CONFIG_PATH = Path(__file__).parent / 'config.json'


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print('[error] config.json not found. Copy config.example.json to config.json and fill in your keys.')
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def fetch_tweets(cfg: dict) -> dict:
    """Fetch tweets using the configured provider. Returns {'tweets': [...]}."""
    tw_cfg = cfg['twitter']
    provider = tw_cfg.get('provider', '6551')
    fetch_count = cfg.get('sync', {}).get('fetch_count', 20)

    if provider == '6551':
        import twitter_6551 as t6
        token = tw_cfg.get('6551_token', '')
        username = tw_cfg.get('username', '')
        if not token or not username:
            return {'error': '6551_token and username required in config'}
        return t6.get_user_tweets(token, username, count=fetch_count)
    elif provider == 'xapi':
        import xapi_client as xapi
        api_key = tw_cfg.get('xapi_key', '')
        user_id = tw_cfg.get('user_id', '')
        if not api_key or not user_id:
            return {'error': 'xapi_key and user_id required in config'}
        return xapi.get_user_tweets(api_key, user_id, count=fetch_count)
    else:
        return {'error': f'unknown provider: {provider}'}


def enrich_tweet(cfg: dict, tweet: dict) -> dict:
    """
    Enrich tweet with full text and media URLs if not already present.
    6551 returns these natively; xapi needs an extra GraphQL call.
    """
    provider = cfg['twitter'].get('provider', '6551')

    if provider == '6551':
        # 6551 already returns full text and media
        return {
            'note_text': tweet.get('full_text', ''),
            'media_urls': tweet.get('media_urls', []),
        }

    # xapi: need GraphQL call for long tweets
    import xapi_client as xapi
    api_key = cfg['twitter'].get('xapi_key', '')
    tweet_id = tweet.get('id') or tweet.get('id_str', '')
    detail = xapi.get_tweet_detail(api_key, tweet_id)
    if 'error' not in detail:
        return {
            'note_text': detail.get('full_text', ''),
            'media_urls': detail.get('media_urls', []),
        }
    return {'note_text': '', 'media_urls': []}


# ── Core sync ────────────────────────────────────────────────────────────────

def sync_once(cfg: dict, dry_run: bool = False) -> dict:
    stats = {'fetched': 0, 'skipped': 0, 'already_posted': 0, 'published': 0, 'errors': 0}

    bsq_key = cfg['binance_square']['api_key']
    sync_cfg = cfg.get('sync', {})
    daily_limit = sync_cfg.get('daily_post_limit', 12)
    posts_per_run = sync_cfg.get('posts_per_run', 1)
    max_text_len = sync_cfg.get('max_text_length', 900)

    # Check daily limit
    today_count = db.posted_count_today()
    if today_count >= daily_limit:
        print(f'[sync] daily limit reached ({today_count}/{daily_limit}), skipping')
        return stats

    remaining = min(posts_per_run, daily_limit - today_count)
    print(f'[sync] posted today: {today_count}, will post up to {remaining}')

    # Fetch tweets
    result = fetch_tweets(cfg)
    if 'error' in result:
        print(f'[sync] failed to fetch tweets: {result["error"]}')
        stats['errors'] += 1
        return stats

    tweets = result.get('tweets', [])
    stats['fetched'] = len(tweets)
    print(f'[sync] fetched {len(tweets)} tweets')

    # Process oldest first
    published_this_run = 0
    for tweet in reversed(tweets):
        if published_this_run >= remaining:
            break

        tweet_id = tweet.get('id') or tweet.get('id_str', '')
        if not tweet_id:
            continue

        if db.is_posted(tweet_id):
            stats['already_posted'] += 1
            continue

        ok, reason = fil.should_sync(tweet)
        if not ok:
            print(f'  skip [{tweet_id}] reason={reason}')
            stats['skipped'] += 1
            if not dry_run:
                db.mark_posted(tweet_id, 'filtered')
            continue

        # Enrich with full text / media
        enriched = enrich_tweet(cfg, tweet)
        note_text = enriched.get('note_text', '')

        if note_text and len(note_text) > len(tweet.get('full_text', '')):
            print(f'    [long tweet] full text: {len(note_text)} chars')

        text = fil.prepare_text(tweet, note_tweet_text=note_text, max_len=max_text_len)
        print(f'  post [{tweet_id}] {text[:60]}{"..." if len(text) > 60 else ""}')

        res = pub.publish(text, bsq_key, dry_run=dry_run)
        if res['ok']:
            if not dry_run:
                db.mark_posted(tweet_id, res['post_id'])
            stats['published'] += 1
            published_this_run += 1
            if not dry_run:
                print(f'    => {res["url"]}')
        else:
            code = res.get('code', '')
            print(f'    => failed code={code} msg={res.get("message", "")}')
            stats['errors'] += 1
            if code == pub.DAILY_LIMIT_CODE:
                print('[sync] Binance daily post limit reached, stopping')
                break
            if code in pub.AUTH_ERROR_CODES:
                print('[sync] Binance API key invalid, please check config')
                sys.exit(1)

    return stats


def show_status():
    import sqlite3
    db.init_db()
    con = sqlite3.connect(db.DB_PATH)
    today = con.execute("SELECT COUNT(*) FROM posted_tweets WHERE posted_at >= date('now')").fetchone()[0]
    total = con.execute('SELECT COUNT(*) FROM posted_tweets').fetchone()[0]
    real_posts = con.execute("SELECT COUNT(*) FROM posted_tweets WHERE square_post_id != 'filtered'").fetchone()[0]
    cursor = con.execute("SELECT value FROM sync_state WHERE key='cursor'").fetchone()
    print(f'Posted today: {today}')
    print(f'Total: {total} (published: {real_posts}, filtered: {total - real_posts})')
    print(f'Cursor: {cursor[0][:30] if cursor and cursor[0] else "none"}...')
    con.close()


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Twitter → Binance Square sync tool')
    parser.add_argument('--dry-run', action='store_true', help='Preview without posting')
    parser.add_argument('--reset', action='store_true', help='Clear cursor (re-fetch all)')
    parser.add_argument('--status', action='store_true', help='Show sync statistics')
    args = parser.parse_args()

    db.init_db()

    if args.status:
        show_status()
        return

    if args.reset:
        db.save_cursor('')
        print('[sync] cursor cleared')
        return

    cfg = load_config()

    if args.dry_run:
        print('[sync] DRY-RUN mode')

    provider = cfg['twitter'].get('provider', '6551')
    print(f'[sync] twitter provider: {provider}')

    start = time.time()
    stats = sync_once(cfg, dry_run=args.dry_run)
    elapsed = time.time() - start
    print(
        f'\n[sync] done in {elapsed:.1f}s | '
        f'fetched={stats["fetched"]} skipped={stats["skipped"]} '
        f'already_posted={stats["already_posted"]} published={stats["published"]} errors={stats["errors"]}'
    )


if __name__ == '__main__':
    main()
