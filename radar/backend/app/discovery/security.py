import asyncio
import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeDiscoveryUrl(ValueError):
    pass


def normalize_discovery_url(url: str) -> str:
    value = url.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeDiscoveryUrl("discovery URL must use http or https")
    if not parsed.hostname:
        raise UnsafeDiscoveryUrl("discovery URL must include a hostname")
    if parsed.username or parsed.password:
        raise UnsafeDiscoveryUrl("credentials are not allowed in discovery URLs")
    if parsed.port not in {None, 80, 443}:
        raise UnsafeDiscoveryUrl("discovery URL must use port 80 or 443")
    host = parsed.hostname.casefold()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise UnsafeDiscoveryUrl("local network hosts are not allowed")
    return value


def _resolved_addresses(host: str, port: int) -> set[str]:
    return {item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}


async def ensure_public_url(url: str) -> str:
    value = normalize_discovery_url(url)
    parsed = urlparse(value)
    assert parsed.hostname is not None
    try:
        literal = ipaddress.ip_address(parsed.hostname)
        addresses = {str(literal)}
    except ValueError:
        try:
            addresses = await asyncio.to_thread(
                _resolved_addresses,
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
            )
        except socket.gaierror as exc:
            raise UnsafeDiscoveryUrl("discovery hostname could not be resolved") from exc

    if not addresses:
        raise UnsafeDiscoveryUrl("discovery hostname did not resolve")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise UnsafeDiscoveryUrl("discovery URL resolves to a non-public network address")
    return value
