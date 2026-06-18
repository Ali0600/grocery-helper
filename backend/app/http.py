"""A shared httpx client that counts every outbound request (see `app/metrics.py`).

All scrapers/locators build their clients here so each call to an external site is
tallied by host via an httpx `request` event hook.
"""
from __future__ import annotations

from typing import Optional

import httpx

from . import metrics


def _on_request(request: httpx.Request) -> None:
    metrics.record(request.url.host)


def tracked_client(*, timeout: float, headers: Optional[dict] = None) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=headers,
        event_hooks={"request": [_on_request]},
    )
