"""
xapi.to client with built-in rate limiting.

Rate limiting:
- Min 3 seconds between calls
- Max 15 calls per 60-second window
- Auto-waits when limit is reached
"""
from __future__ import annotations

import urllib.request
import json
import subprocess
import time
import re
import threading
from collections import deque

MIN_INTERVAL_SEC = 3.0
MAX_CALLS_PER_MIN = 15
CALL_WINDOW_SEC = 60.0

_lock = threading.Lock()
_last_call_time = 0.0
_call_timestamps: deque = deque()


def _wait_for_slot():
    global _last_call_time
    with _lock:
        now = time.monotonic()
        while _call_timestamps and now - _call_timestamps[0] > CALL_WINDOW_SEC:
            _call_timestamps.popleft()
        if len(_call_timestamps) >= MAX_CALLS_PER_MIN:
            wait_until = _call_timestamps[0] + CALL_WINDOW_SEC
            sleep_for = wait_until - now
            if sleep_for > 0:
                print(f'[xapi] rate limit reached, waiting {sleep_for:.1f}s ...')
                time.sleep(sleep_for)
                now = time.monotonic()
                while _call_timestamps and now - _call_timestamps[0] > CALL_WINDOW_SEC:
                    _call_timestamps.popleft()
        elapsed = now - _last_call_time
        if elapsed < MIN_INTERVAL_SEC:
            time.sleep(MIN_INTERVAL_SEC - elapsed)
            now = time.monotonic()
        _last_call_time = now
        _call_timestamps.append(now)


def _headers(api_key: str):
    return {
        'XAPI-Key': api_key,
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Origin': 'https://xapi.to',
    }


def execute(api_key: str, action_id: str, input_data: dict, timeout: int = 20) -> dict:
    _wait_for_slot()
    payload = json.dumps({'action_id': action_id, 'input': input_data}).encode()
    req = urllib.request.Request(
        'https://c.xapi.to/v1/actions/execute',
        data=payload, headers=_headers(api_key), method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read())
            if resp.get('success') is False:
                return {'error': resp.get('error', {})}
            return resp.get('data', resp)
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return {'error': json.loads(body)}
        except Exception:
            return {'error': {'code': str(e.code), 'message': body[:200].decode('utf-8', errors='replace')}}
    except Exception as e:
        return {'error': {'code': 'CLIENT_ERROR', 'message': str(e)}}


def get_user_tweets(api_key: str, user_id: str, count: int = 20) -> dict:
    result = execute(api_key, 'twitter.user_tweets', {'user_id': user_id, 'count': count})
    if 'error' in result:
        return result
    return {'tweets': result.get('tweets', []), 'cursors': result.get('cursors', {})}


def get_tweet_detail(api_key: str, tweet_id: str, timeout: int = 30) -> dict:
    """
    Fetch full tweet content via GraphQL TweetDetail.
    Returns {'full_text': ..., 'media_urls': [...]} or {'error': ...}.
    Handles long tweets (note_tweet) that are truncated by the standard API.
    """
    mcp_url = f'https://mcp.xapi.to/mcp?apikey={api_key}'
    variables = json.dumps({
        'focalTweetId': tweet_id,
        'with_rux_injections': False,
        'includePromotedContent': False,
        'withCommunity': True,
        'withQuickPromoteEligibilityTweetFields': True,
        'withBirdwatchNotes': True,
        'withVoice': True,
        'withV2Timeline': True,
    })
    payload = json.dumps({
        'jsonrpc': '2.0', 'id': 1,
        'method': 'tools/call',
        'params': {
            'name': 'CALL',
            'arguments': {
                'action_id': 'twitter.graphql_TweetDetail',
                'arguments': {'params': {'variables': variables}},
            },
        },
    })

    try:
        result = subprocess.run(
            ['curl', '-s', '-X', 'POST', mcp_url,
             '-H', 'Content-Type: application/json',
             '-H', 'Accept: application/json, text/event-stream',
             '-d', payload],
            capture_output=True, text=True, timeout=timeout,
        )
        if not result.stdout.strip():
            return {'error': 'empty response from MCP'}
        resp = json.loads(result.stdout)
        text_content = resp.get('result', {}).get('content', [{}])[0].get('text', '')
        if not text_content:
            return {'error': 'no text in MCP response'}
        inner = json.loads(text_content)
    except Exception as e:
        return {'error': str(e)}

    full_text = ''
    media_urls = []

    def _extract(obj, depth=0):
        nonlocal full_text, media_urls
        if depth > 20 or not isinstance(obj, (dict, list)):
            return
        if isinstance(obj, dict):
            note = obj.get('note_tweet', {})
            if note:
                nt_text = (note.get('note_tweet_results', {})
                           .get('result', {}).get('text', ''))
                if nt_text and len(nt_text) > len(full_text):
                    full_text = nt_text
            if obj.get('rest_id') == tweet_id:
                legacy = obj.get('legacy', {})
                ft = legacy.get('full_text', '')
                if ft and not full_text:
                    full_text = ft
                media_list = (legacy.get('extended_entities', {}).get('media', [])
                              or legacy.get('entities', {}).get('media', []))
                for m in media_list:
                    url = m.get('media_url_https', '')
                    if url:
                        media_urls.append(url)
            for v in obj.values():
                _extract(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                _extract(item, depth + 1)

    _extract(inner)

    if not media_urls:
        found = set(re.findall(r'https://pbs\.twimg\.com/media/[^"\\]+', json.dumps(inner)))
        media_urls = sorted(found)

    if not full_text:
        return {'error': 'tweet not found in response'}

    return {'full_text': full_text, 'media_urls': media_urls}
