"""HTTP transport to Apple, with a guard and the correct trust anchor.

Two quirks of Apple's endpoints that are handled centrally here:

* ``gsa.apple.com`` is **not** signed by a public CA but by Apple's private
  "Apple Server Authentication CA". With the system trust store every
  connection fails with CERTIFICATE_VERIFY_FAILED. We ship the chain and
  verify against it - instead of switching verification off.
* Every GSA request must carry a harmless ``X-MMe-Client-Info``. The guard
  checks this *before* sending, so a forgotten header shows up as a clear
  local exception rather than as Apple's 503 smoke screen.
"""

from __future__ import annotations

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import GSA_CA_BUNDLE
from ..errors import AnisetteClientInfoRejected, AppleRateLimited
from ..i18n import _
from . import clientinfo

GSA_HOST = "gsa.apple.com"
GSA_URL = f"https://{GSA_HOST}/grandslam/GsService2"
DEV_SERVICES = "https://developerservices2.apple.com/services"

#: Apple's protocol version in the .action paths.
PROTOCOL_VERSION = "QH65B2"

USER_AGENT_AKD = "akd/1.0 CFNetwork/1494.0.7 Darwin/23.4.0"
USER_AGENT_XCODE = "Xcode"

#: The signature of the edge rejection: HTTP 503 with a tiny HTML page.
#: A real outage looks different, so we may tell the two apart.
_EDGE_REJECT_MAX_BODY = 512


class _GuardedSession(requests.Session):
    """Session that checks the client info before every GSA request."""

    def request(self, method, url, **kwargs):  # type: ignore[override]
        if GSA_HOST in str(url):
            headers = {**(self.headers or {}), **(kwargs.get("headers") or {})}
            ci = next((v for k, v in headers.items()
                       if k.lower() == "x-mme-client-info"), None)
            clientinfo.assert_safe(ci, where=f"{method} {url}")
        return super().request(method, url, **kwargs)


def _retrying_adapter(*, retry_statuses: tuple[int, ...]) -> HTTPAdapter:
    retry = Retry(total=3, backoff_factor=0.5,
                  status_forcelist=retry_statuses,
                  allowed_methods=frozenset({"GET", "POST"}))
    return HTTPAdapter(max_retries=retry)


#: During sign-in **nothing** is retried automatically.
#:
#: Not 429, because a retry only escalates Apple's throttling - and because
#: the ``complete`` step carries a one-time cookie from ``init``, and sending
#: it again amounts to a replay.
#: Not 503, because with GSA that is practically always the client info
#: rejection.
_NO_RETRY: tuple[int, ...] = ()

#: With the developer API, real server errors can be retried - there is no
#: handshake state there that could break. 429 stays excluded here too.
_DEV_RETRY: tuple[int, ...] = (500, 502, 504)


#: Apple's edge allows exactly *one* request to GsService2 per TCP
#: connection. Every further one on the same connection gets HTTP 429 -
#: measured: [404, 429, 429, 429, 429, 429] with reuse versus
#: [404, 404, 404, 404, 404, 429] with ``Connection: close``.
#:
#: Otherwise this is exactly what reproducibly breaks a login: ``init`` is
#: the first request and goes through, ``complete`` the second and gets
#: rejected. That looks like the account being throttled, but it isn't.
_FORCE_CLOSE = {"Connection": "close"}

#: The remaining 429 is a rolling budget per IP address and clears up on its
#: own. Because the edge rejects *before* the auth service, the SRP cookie is
#: not consumed - so another attempt is harmless.
GSA_MAX_ATTEMPTS = 4
GSA_RETRY_DELAY = 2.0


def gsa_session() -> requests.Session:
    s = _GuardedSession()
    s.verify = str(GSA_CA_BUNDLE)
    s.headers.update({
        "Content-Type": "text/x-xml-plist",
        "Accept": "*/*",
        "User-Agent": USER_AGENT_AKD,
        "Accept-Language": "en-us",
        **_FORCE_CLOSE,
    })
    s.mount("https://", _retrying_adapter(retry_statuses=_NO_RETRY))
    return s


def gsa_request(session: requests.Session, method: str, url: str,
                *, client_info: str, headers: dict[str, str] | None = None,
                timeout: float = 30.0, **kwargs) -> requests.Response:
    """A GSA request on a fresh connection, with limited retries.

    Retries happen only on the edge's HTTP 429 - and deliberately by hand
    here rather than via urllib3, so every retry gets a new connection and
    the count stays clearly bounded.
    """
    merged = {**(headers or {}), **_FORCE_CLOSE}
    last: requests.Response | None = None

    for attempt in range(1, GSA_MAX_ATTEMPTS + 1):
        # Empty the connection pool: the next request must get its own TCP
        # connection, otherwise the edge answers with 429 again.
        session.close()
        response = session.request(method, url, headers=merged,
                                   timeout=timeout, **kwargs)
        check_edge_rejection(response, client_info)
        if response.status_code != 429:
            return response
        last = response
        if attempt < GSA_MAX_ATTEMPTS:
            time.sleep(GSA_RETRY_DELAY * attempt)

    assert last is not None
    check_rate_limit(last, what="Apple's sign-in service",
                     attempts=GSA_MAX_ATTEMPTS)
    return last


def dev_session() -> requests.Session:
    """For developerservices2 - public CA, and the Xcode user agent is
    perfectly fine here. Only GSA is picky."""
    s = requests.Session()
    s.headers.update({
        "Content-Type": "text/x-xml-plist",
        "User-Agent": USER_AGENT_XCODE,
        "Accept": "text/x-xml-plist",
        "Accept-Language": "en-us",
    })
    s.mount("https://", _retrying_adapter(retry_statuses=_DEV_RETRY))
    return s


def check_edge_rejection(response: requests.Response, client_info: str) -> None:
    """Translates Apple's 503 smoke screen into a diagnosis.

    To be called after every GSA request. A 503 with a tiny body practically
    always means the client info string was rejected at the edge - not that
    Apple is down.
    """
    if response.status_code != 503:
        return
    if len(response.content) > _EDGE_REJECT_MAX_BODY:
        return
    raise AnisetteClientInfoRejected(_(
        "Apple rejected the request at the edge (HTTP 503, {size} bytes). "
        "That is not an outage but a rejection of the client info string. "
        "Sent was:\n  {sent}\nExpected is a string containing {wanted!r}.",
        size=len(response.content), sent=client_info,
        wanted=clientinfo.AKD_IDENTIFIER))


def check_rate_limit(response: requests.Response, *, what: str = "Apple",
                     attempts: int = 1) -> None:
    """Translates HTTP 429 into a message with a waiting time.

    Only relevant once fresh connections are rejected too - then the IP
    address's budget, shared by all sign-ins on the same network, is used
    up.
    """
    if response.status_code != 429:
        return
    retry_after = response.headers.get("Retry-After", "")
    wait = ""
    if retry_after.isdigit():
        secs = int(retry_after)
        wait = (" " + _("Apple says {minutes} minutes.", minutes=secs // 60)
                if secs >= 60
                else " " + _("Apple says {seconds} seconds.", seconds=secs))

    # Apple occasionally includes a reason. Keep it - on the next attempt
    # it is the only clue we have.
    detail = ""
    body = (response.content or b"")[:400].decode("utf-8", "replace").strip()
    if body:
        detail = "\n" + _("Apple’s reply: {body}", body=body)
    for header in ("X-Apple-I-Request-ID", "X-Apple-Edge-Response", "X-Apple-Jingle-Correlation-Key"):
        if header in response.headers:
            detail += f"\n{header}: {response.headers[header]}"

    raise AppleRateLimited(_(
        "{what} still throttled on a fresh connection after {attempts} "
        "attempts (HTTP 429).{wait}\nApple keeps a budget per IP address "
        "that every sign-in on the same network shares. Wait a few minutes "
        "and try again.", what=what, attempts=attempts, wait=wait) + detail)
