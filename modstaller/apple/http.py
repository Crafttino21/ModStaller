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

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import GSA_CA_BUNDLE
from ..errors import AnisetteClientInfoRejected, AppleRateLimited
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


def _retrying_adapter(*, retry_statuses: tuple[int, ...]) -> HTTPAdapter:
    retry = Retry(total=3, backoff_factor=0.5,
                  status_forcelist=retry_statuses,
                  allowed_methods=frozenset({"GET", "POST"}))
    return HTTPAdapter(max_retries=retry)


#: Beim Anmelden wird **nichts** automatisch wiederholt.
#:
#: 429 nicht, weil ein Retry Apples Drosselung nur eskalieren laesst - und
#: weil der ``complete``-Schritt ein Einmal-Cookie aus ``init`` traegt, das
#: erneut zu senden einem Replay gleichkommt.
#: 503 nicht, weil das bei GSA praktisch immer die Client-Info-Ablehnung ist.
_NO_RETRY: tuple[int, ...] = ()

#: Bei der Entwickler-API sind echte Serverfehler wiederholbar - dort gibt es
#: keinen Handshake-Zustand, der dabei kaputtgehen koennte. 429 bleibt auch
#: hier aussen vor.
_DEV_RETRY: tuple[int, ...] = (500, 502, 504)


#: Apples Edge erlaubt pro TCP-Verbindung genau *einen* Request an
#: GsService2. Jeder weitere auf derselben Verbindung bekommt HTTP 429 -
#: gemessen: [404, 429, 429, 429, 429, 429] bei Wiederverwendung gegenueber
#: [404, 404, 404, 404, 404, 429] mit ``Connection: close``.
#:
#: Genau daran scheitert ein Login sonst reproduzierbar: ``init`` ist der
#: erste Request und geht durch, ``complete`` der zweite und wird abgewiesen.
#: Das sieht nach Drosselung des Accounts aus, ist aber keine.
_FORCE_CLOSE = {"Connection": "close"}

#: Der Rest-429 ist ein rollendes Budget pro IP-Adresse und klart von selbst
#: auf. Weil die Edge *vor* dem Auth-Dienst abweist, wird das SRP-Cookie dabei
#: nicht verbraucht - ein erneuter Versuch ist deshalb unbedenklich.
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
    """Ein GSA-Request auf frischer Verbindung, mit begrenzter Wiederholung.

    Wiederholt wird ausschliesslich bei HTTP 429 der Edge - und bewusst hier
    von Hand statt ueber urllib3, damit die Wiederholung immer eine neue
    Verbindung bekommt und die Anzahl klar begrenzt bleibt.
    """
    merged = {**(headers or {}), **_FORCE_CLOSE}
    last: requests.Response | None = None

    for attempt in range(1, GSA_MAX_ATTEMPTS + 1):
        # Verbindungspool leeren: die naechste Anfrage soll eine eigene
        # TCP-Verbindung bekommen, sonst antwortet die Edge wieder mit 429.
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
    check_rate_limit(last, what="Apples Anmeldedienst",
                     attempts=GSA_MAX_ATTEMPTS)
    return last


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
    s.mount("https://", _retrying_adapter(retry_statuses=_DEV_RETRY))
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


def check_rate_limit(response: requests.Response, *, what: str = "Apple",
                     attempts: int = 1) -> None:
    """Uebersetzt HTTP 429 in eine Ansage mit Wartezeit.

    Erst relevant, wenn auch frische Verbindungen abgewiesen werden - dann
    ist das Budget der IP-Adresse aufgebraucht, das sich alle Anmeldungen im
    selben Netz teilen.
    """
    if response.status_code != 429:
        return
    retry_after = response.headers.get("Retry-After", "")
    wait = ""
    if retry_after.isdigit():
        secs = int(retry_after)
        wait = (f" Apple nennt {secs // 60} Minuten." if secs >= 60
                else f" Apple nennt {secs} Sekunden.")

    # Apple legt gelegentlich einen Grund bei. Mitnehmen - beim naechsten
    # Versuch ist das der einzige Anhaltspunkt, den wir haben.
    detail = ""
    body = (response.content or b"")[:400].decode("utf-8", "replace").strip()
    if body:
        detail = f"\nApples Antwort: {body}"
    for header in ("X-Apple-I-Request-ID", "X-Apple-Edge-Response", "X-Apple-Jingle-Correlation-Key"):
        if header in response.headers:
            detail += f"\n{header}: {response.headers[header]}"

    raise AppleRateLimited(
        f"{what} hat auch nach {attempts} Versuchen auf frischer Verbindung "
        f"gedrosselt (HTTP 429).{wait}\n"
        "Apple fuehrt ein Budget pro IP-Adresse, das sich alle Anmeldungen im "
        "selben Netz teilen. Ein paar Minuten warten und erneut versuchen."
        + detail
    )
