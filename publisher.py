"""
Binance Square publishing client.

Endpoint: POST https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add
Auth: X-Square-OpenAPI-Key header
"""
from __future__ import annotations

import urllib.request
import json

ENDPOINT = 'https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add'


def publish(text: str, api_key: str, dry_run: bool = False) -> dict:
    """
    Post to Binance Square.

    Returns:
        {'ok': True,  'post_id': '...', 'url': '...'}
        {'ok': False, 'code': '...', 'message': '...'}
    """
    if dry_run:
        preview = f'{text[:80]}...' if len(text) > 80 else text
        print(f'  [dry-run] would publish: {preview}')
        return {'ok': True, 'post_id': 'dry-run', 'url': ''}

    payload = json.dumps({'bodyTextOnly': text}).encode('utf-8')
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            'X-Square-OpenAPI-Key': api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read())
    except Exception as e:
        return {'ok': False, 'code': 'REQUEST_ERROR', 'message': str(e)}

    code = resp.get('code', '')
    if code == '000000':
        post_id = str(resp.get('data', {}).get('id', ''))
        return {
            'ok': True,
            'post_id': post_id,
            'url': f'https://www.binance.com/square/post/{post_id}',
        }

    message = resp.get('messageDetail') or resp.get('message') or ''
    return {'ok': False, 'code': code, 'message': message}


DAILY_LIMIT_CODE = '220009'
AUTH_ERROR_CODES = {'220003', '220004'}
