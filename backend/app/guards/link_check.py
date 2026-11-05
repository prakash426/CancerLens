"""Source-link verification (dead outbound citations stay unlinked, never dropped).

Upstream records occasionally carry ``canonical_url`` values that do not
resolve (redirect loops, withdrawn pages, DNS failures). The fact text and
attribution are still shown; only the hyperlink is withheld when a fetch
proves the URL dead. Anything ambiguous (bot-wall 403s, transient 5xx,
timeouts, non-https URLs) keeps the link: a false visible link beats a
falsely hidden one.

Every fetch passes the SSRF guard first, so a compromised upstream record
cannot turn verification into an internal-network probe.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from ..config import create_verified_ssl_context
from .ssrf_url_guard import Resolver, guard_public_url

logger = logging.getLogger("cancerlens.link_check")

_CHECK_TIMEOUT_SECONDS = 8.0
_CHECK_MAX_REDIRECTS = 5
_CHECK_MAX_URLS = 64
_CHECK_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
    "User-Agent": "CancerLens/1.0 (source-link verification)",
}
_DEAD_STATUSES = frozenset({404, 410})


async def verify_source_links(
    urls: list[str],
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    resolver: Resolver | None = None,
) -> dict[str, bool]:
    """Fetch each URL once and report aliveness. Never raises; uncheckable means alive."""
    targets = list(dict.fromkeys(u.strip() for u in urls if u and u.strip()))[:_CHECK_MAX_URLS]
    if not targets:
        return {}
    async with httpx.AsyncClient(
        verify=create_verified_ssl_context(),
        timeout=_CHECK_TIMEOUT_SECONDS,
        follow_redirects=True,
        max_redirects=_CHECK_MAX_REDIRECTS,
        headers=_CHECK_HEADERS,
        transport=transport,
    ) as client:

        async def _one(url: str) -> tuple[str, bool]:
            try:
                guard_public_url(url, resolver=resolver)
            except ValueError:
                return url, True  # non-https or guard-blocked: not verifiable, keep visible
            try:
                # Final status after following redirects; the body is never read.
                async with client.stream("GET", url) as response:
                    status = response.status_code
            except httpx.TooManyRedirects:
                return url, False
            except httpx.ConnectError:
                return url, False
            except httpx.HTTPError:
                return url, True  # timeouts and transport noise are transient: benefit of the doubt
            return url, status not in _DEAD_STATUSES

        return dict(await asyncio.gather(*(_one(url) for url in targets)))


__all__ = ["verify_source_links"]
