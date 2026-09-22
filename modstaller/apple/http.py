"""HTTP-Transport zu Apple, mit Guard und korrektem Trust-Anchor.

Zwei Eigenheiten von Apples Endpunkten, die hier zentral behandelt werden:

* ``gsa.apple.com`` wird **nicht** von einer oeffentlichen CA signiert, sondern
  von Apples privater "Apple Server Authentication CA". Mit dem System-Trust-
  Store scheitert jede Verbindung an CERTIFICATE_VERIFY_FAILED. Wir liefern die
  Kette mit und verifizieren dagegen - statt die Pruefung abzuschalten.
* Jeder GSA-Request muss eine unbedenkliche ``X-MMe-Client-Info`` tragen.
  Der Guard prueft das *vor* dem Absenden, damit ein vergessener Header als
  klare lokale Ausnahme auffaellt und nicht als Apples 503-Nebelkerze.
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import GSA_CA_BUNDLE
from ..errors import AnisetteClientInfoRejected
from . import clientinfo

GSA_HOST = "gsa.apple.com"
GSA_URL = f"https://{GSA_HOST}/grandslam/GsService2"
DEV_SERVICES = "https://developerservices2.apple.com/services"

#: Apples Protokollversion in den .action-Pfaden.
PROTOCOL_VERSION = "QH65B2"

USER_AGENT_AKD = "akd/1.0 CFNetwork/1494.0.7 Darwin/23.4.0"
USER_AGENT_XCODE = "Xcode"

#: Die Signatur der Edge-Ablehnung: HTTP 503 mit winziger HTML-Seite.
#: Ein echter Ausfall sieht anders aus, deshalb duerfen wir das unterscheiden.
_EDGE_REJECT_MAX_BODY = 512


class _GuardedSession(requests.Session):
    """Session, die vor jedem GSA-Request die Client-Info prueft."""

    def request(self, method, url, **kwargs):  # type: ignore[override]
        if GSA_HOST in str(url):
            headers = {**(self.headers or {}), **(kwargs.get("headers") or {})}
            ci = next((v for k, v in headers.items()
                       if k.lower() == "x-mme-client-info"), None)
            clientinfo.assert_safe(ci, where=f"{method} {url}")
        return super().request(method, url, **kwargs)


def _retrying_adapter() -> HTTPAdapter:
    # Bewusst *ohne* 503: ein 503 von GSA ist meist die Client-Info-Ablehnung,
    # und die wegzuretryen verschleiert nur die Ursache.
    retry = Retry(total=3, backoff_factor=0.5,
                  status_forcelist=(429, 500, 502, 504),
                  allowed_methods=frozenset({"GET", "POST"}))
    return HTTPAdapter(max_retries=retry)


def gsa_session() -> requests.Session:
    s = _GuardedSession()
    s.verify = str(GSA_CA_BUNDLE)
    s.headers.update({
        "Content-Type": "text/x-xml-plist",
        "Accept": "*/*",
        "User-Agent": USER_AGENT_AKD,
        "X-Mme-Nas-Qualify": "true",
        "Accept-Language": "en-us",
    })
    s.mount("https://", _retrying_adapter())
    return s


def dev_session() -> requests.Session:
    """Fuer developerservices2 - oeffentliche CA, und hier ist der
    Xcode-User-Agent voellig in Ordnung. Nur GSA ist waehlerisch."""
    s = requests.Session()
    s.headers.update({
        "Content-Type": "text/x-xml-plist",
        "User-Agent": USER_AGENT_XCODE,
        "Accept": "text/x-xml-plist",
        "Accept-Language": "en-us",
    })
    s.mount("https://", _retrying_adapter())
    return s


def check_edge_rejection(response: requests.Response, client_info: str) -> None:
    """Uebersetzt Apples 503-Nebelkerze in eine Diagnose.

    Aufzurufen nach jedem GSA-Request. Ein 503 mit winzigem Body bedeutet
    praktisch immer: der Client-Info-String wurde an der Edge abgewiesen -
    nicht, dass Apple ausgefallen ist.
    """
    if response.status_code != 503:
        return
    if len(response.content) > _EDGE_REJECT_MAX_BODY:
        return
    raise AnisetteClientInfoRejected(
        "Apple hat den Request an der Edge abgewiesen (HTTP 503, "
        f"{len(response.content)} Byte). Das ist kein Ausfall, sondern eine "
        "Ablehnung des Client-Info-Strings. Gesendet wurde:\n"
        f"  {client_info}\n"
        f"Erwartet wird ein String mit {clientinfo.AKD_IDENTIFIER!r}."
    )
