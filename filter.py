"""
Tweet filter: only sync original text tweets to Binance Square.

Filters out:
1. Retweets
2. Replies
3. Empty text (media-only)
4. Text too short (< 5 chars)
"""
from __future__ import annotations

import re

_URL_RE = re.compile(r'https?://t\.co/\S+')


def _clean_text(full_text: str) -> str:
    return _URL_RE.sub('', full_text).strip()


def should_sync(tweet: dict) -> tuple:
    """Returns (should_sync: bool, skip_reason: str)."""
    if tweet.get('is_retweet'):
        return False, 'retweet'
    if tweet.get('in_reply_to_status_id_str') or tweet.get('in_reply_to_status_id'):
        return False, 'reply'
    text = _clean_text(tweet.get('full_text', ''))
    if not text:
        return False, 'empty_text'
    if len(text) < 5:
        return False, f'too_short({len(text)})'
    return True, ''


def prepare_text(tweet: dict, note_tweet_text: str = '', max_len: int = 900) -> str:
    """
    Clean and truncate tweet text for Binance Square.
    Prefers note_tweet_text (full long tweet) over tweet['full_text'].
    """
    raw = note_tweet_text if note_tweet_text else tweet.get('full_text', '')
    text = _clean_text(raw)
    if len(text) > max_len:
        text = text[:max_len - 3] + '...'
    return text
