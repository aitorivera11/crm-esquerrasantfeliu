import os

import requests


UPCITEMDB_TRIAL_ENDPOINT = 'https://api.upcitemdb.com/prod/trial/lookup'
UPCITEMDB_PRO_ENDPOINT = 'https://api.upcitemdb.com/prod/v1/lookup'


def lookup_product_by_barcode(upc: str):
    """Return normalized product data from UPCitemdb or None when unavailable."""
    upc = (upc or '').strip()
    if not upc:
        return None

    api_key = os.getenv('UPCITEMDB_USER_KEY', '').strip()
    key_type = os.getenv('UPCITEMDB_KEY_TYPE', '3scale').strip()

    endpoint = UPCITEMDB_PRO_ENDPOINT if api_key else UPCITEMDB_TRIAL_ENDPOINT
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    if api_key:
        headers.update({'user_key': api_key, 'key_type': key_type})

    response = requests.post(endpoint, json={'upc': upc}, headers=headers, timeout=6)
    response.raise_for_status()

    payload = response.json()
    items = payload.get('items') or []
    if not items:
        return None

    item = items[0]
    return {
        'title': item.get('title') or '',
        'brand': item.get('brand') or '',
        'category': item.get('category') or '',
        'description': item.get('description') or '',
    }
