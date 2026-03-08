"""
6551.io Twitter API client.

Advantages over xapi.to:
- Returns full long tweet text natively (no extra GraphQL call needed)
- Returns media URLs directly
- Queries by username (no user_id lookup needed)
"""
from __future__ import annotations

import urllib.request
import json
import re

BASE_URL = 'https://ai.6551.io'

_URL_RE = re.compile(r'https?://t\.co/\S+')


def _headers(token: str):
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0',
    }


def _post(token: str, path: str, body: dict, timeout: int = 30) -> dict:
    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        f'{BASE_URL}{path}',
        data=payload, headers=_headers(token), method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return {'success': False, 'error': json.loads(raw)}
        except Exception:
            return {'success': False, 'error': raw[:200].decode('utf-8', errors='replace')}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_user_tweets(token: str, username: str, count: int = 20) -> dict:
    """
    Fetch user tweets. Returns normalized format:
    {'tweets': [{'id': ..., 'full_text': ..., 'media_urls': [...], ...}]}
    """
    resp = _post(token, '/open/twitter_user_tweets', {
        'username': username,
        'maxResults': min(count, 100),
        'product': 'Latest',
        'includeReplies': False,
        'includeRetweets': False,
    })

    if not resp.get('success'):
        return {'error': resp.get('error', 'unknown error')}

    raw_tweets = resp.get('data', [])
    if not isinstance(raw_tweets, list):
        return {'error': 'unexpected response format'}

    tweets = []
    for t in raw_tweets:
        # Normalize to xapi-compatible format
        media_urls = []
        for m in (t.get('media') or []):
            url = m.get('url', '')
            if url:
                media_urls.append(url)

        tweets.append({
            'id': str(t.get('id', '')),
            'id_str': str(t.get('id', '')),
            'full_text': t.get('text', ''),
            'media_urls': media_urls,
            # 6551 already filters replies/retweets server-side
            'is_retweet': False,
            'in_reply_to_status_id_str': None,
        })

    return {'tweets': tweets}
