"""Public URL SSRF guard (SEC-04).

Allows ``https`` on port 443 only, with no embedded credentials. Resolves the
hostname and rejects loopback, private, link-local, CGNAT, multicast, reserved
and unspecified addresses, including IPv4-mapped IPv6. A custom ``resolver``
may be injected so unit tests run offline with zero DNS flakiness.

Residual risk (documented, TESTING Gate 6): DNS is resolved at guard time, so a
record that changes between the check and the fetch (rebinding) is not pinned.
Redirect targets are re-guarded on every hop by the caller.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import urlsplit, urlunsplit

_BLOCKED_SUFFIXES = (".local", ".internal", ".arpa")
_CGNAT = ipaddress.ip_network("100.64.0.0/10")

Resolver = Callable[[str], Sequence[Any]]


def _default_resolver(hostname: str) -> Sequence[Any]:
    return socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)


def _resolved_ips(infos: Sequence[Any] | None) -> list[str]:
    """Accept getaddrinfo-style 5-tuples or plain IP strings (test seams)."""
    ips: list[str] = []
    for info in infos or []:
        sockaddr: Any = info[4] if isinstance(info, (tuple, list)) and len(info) >= 5 else info
        ip_str = sockaddr[0] if isinstance(sockaddr, (tuple, list)) else sockaddr
        ips.append(str(ip_str))
    return ips


def _blocked_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local:
        return True
    if ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True
    if isinstance(ip, ipaddress.IPv4Address) and ip in _CGNAT:
        return True
    return not ip.is_global


def guard_public_url(url: str, resolver: Resolver | None = None) -> str:
    """Validate a public fetch URL. Returns the URL with any #fragment stripped.

    Raises ``ValueError`` on non-https schemes, non-443 ports, embedded
    credentials, blocked hostnames, DNS failures or blocked resolved addresses.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL must be a non-empty string.")
    try:
        parts = urlsplit(url.strip())
    except ValueError as exc:
        raise ValueError(f"Malformed URL: {exc}") from exc
    if parts.scheme.lower() != "https":
        raise ValueError("Only https URLs are allowed.")
    hostname = parts.hostname
    if not hostname:
        raise ValueError("URL must include a hostname.")
    if parts.username is not None or parts.password is not None:
        raise ValueError("Credentials in URLs are not allowed.")
    try:
        port = parts.port
    except ValueError:
        raise ValueError("Invalid port in URL.")
    if port is not None and port != 443:
        raise ValueError("Only the default https port (443) is allowed.")
    lowered = hostname.lower().rstrip(".")
    if lowered == "localhost" or lowered.endswith(_BLOCKED_SUFFIXES):
        raise ValueError(f"Blocked hostname: {hostname}.")
    try:
        infos = (resolver or _default_resolver)(hostname)
    except Exception as exc:
        raise ValueError(f"Could not resolve hostname: {hostname}.") from exc
    ips = _resolved_ips(infos)
    if not ips:
        raise ValueError(f"Hostname resolved to no addresses: {hostname}.")
    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str.split("%")[0])
        except ValueError:
            raise ValueError(f"Unparseable resolved address for {hostname}.")
        candidates: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = [ip]
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            candidates.append(ip.ipv4_mapped)
        if any(_blocked_address(candidate) for candidate in candidates):
            raise ValueError(f"URL resolves to a blocked address ({hostname}).")
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "", parts.query or "", ""))


__all__ = ["Resolver", "guard_public_url"]
