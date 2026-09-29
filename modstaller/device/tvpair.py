"""Pairing an Apple TV or a Vision Pro - over the network.

Neither has a USB port for this. They pair the way Xcode does it, after the
device is told to wait for a computer:

* Apple TV: *Settings › Remotes and Devices › Remote App and Devices*. It
  then shows a PIN, which the user types in here.
* Vision Pro: *Settings › General › Remote Devices*. It asks for consent on
  the device itself.

Both then advertise ``_remotepairing-manual-pairing._tcp``.

pymobiledevice3 has everything for that except the question: it reads the
PIN with ``input()``. :class:`_PinPairing` asks through a callback instead -
the interface (``prompt.pin``) or the terminal - and does so exactly where
pymobiledevice3 would: only for an Apple TV.

The pairing leaves a RemotePairing record (``remote_<identifier>.plist`` in
pymobiledevice3's home folder). With it the Apple TV is found again later by
its ``_remotepairing._tcp`` advert (see ``discovery``), and the developer
tunnel can be built - see ``tunnel.remote_pairing``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from ..errors import DeviceError
from ..i18n import _
from . import discovery, registry

log = logging.getLogger(__name__)

#: How long the pairing advert search listens.
BROWSE_TIMEOUT = 4.0

AskPin = Callable[[str], Awaitable[str | None]]


def kind_of(model: str) -> str:
    """"appletv" or "vision" from the advert's model (``AppleTV14,1``,
    ``RealityDevice14,1``) - for the list to show the right picture."""
    if model.startswith("RealityDevice"):
        return "vision"
    if model.startswith("AppleTV"):
        return "appletv"
    return ""


async def browse(timeout: float = BROWSE_TIMEOUT) -> list[dict]:
    """Apple TVs and Vision Pros waiting to be paired right now."""
    from pymobiledevice3.bonjour import browse_remotepairing_manual_pairing

    out = []
    for answer in await browse_remotepairing_manual_pairing(timeout=timeout):
        host = discovery._pick_address(answer)
        identifier = answer.properties.get("identifier", "")
        if not host or not identifier:
            continue
        model = answer.properties.get("model", "")
        out.append({"name": answer.properties.get("name") or answer.instance.split(".", 1)[0],
                    "identifier": identifier, "host": host, "port": answer.port,
                    "model": model, "kind": kind_of(model)})
    return out


def _pin_pairing_class():
    from pymobiledevice3.exceptions import PairingError
    from pymobiledevice3.remote import tunnel_service as ts

    class _PinPairing(ts.RemotePairingManualPairingService):
        """pymobiledevice3's manual pairing, with the PIN asked for instead of
        read from the terminal."""

        def __init__(self, identifier: str, host: str, port: int, ask_pin: AskPin, name: str,
                     on_step: Callable[[str], None] = lambda m: None):
            super().__init__(identifier, host, port)
            self._ask_pin = ask_pin
            self._name = name
            self._on_step = on_step

        async def _request_pair_consent(self):
            tlv = ts.PairingDataComponentTLVBuf.build([
                {"type": ts.PairingDataComponentType.METHOD, "data": b"\x00"},
                {"type": ts.PairingDataComponentType.STATE, "data": b"\x01"},
            ])
            import platform
            await self._send_pairing_data({
                "data": tlv, "kind": "setupManualPairing",
                "sendingHost": platform.node(), "startNewSession": True,
            })
            response = (await self._receive_plain_response())["event"]["_0"]
            pin = None
            if "pairingRejectedWithError" in response:
                raise PairingError(
                    response["pairingRejectedWithError"]["wrappedError"]["userInfo"]["NSLocalizedDescription"])
            if "awaitingUserConsent" in response:
                # Vision Pro (and iPhones): the device asks - wait for it.
                self._on_step(_("Confirm the pairing on {name} …", name=self._name))
                pairing_data = await self._receive_pairing_data()
            else:
                pairing_data = self._decode_bytes_if_needed(response["pairingData"]["_0"]["data"])
                # tvOS: no consent dialog - it shows a PIN instead. Only
                # there, like pymobiledevice3 itself.
                if "AppleTV" in self.remote_device_model:
                    pin = await self._ask_pin(self._name)
                    if not pin:
                        raise DeviceError(_("Pairing cancelled."))
            data = self.decode_tlv(ts.PairingDataComponentTLVBuf.parse(pairing_data))
            return ts.PairConsentResult(
                public_key=data[ts.PairingDataComponentType.PUBLIC_KEY],
                salt=data[ts.PairingDataComponentType.SALT], pin=pin)

    return _PinPairing


async def _find_paired(identifier: str, timeout: float = BROWSE_TIMEOUT) -> discovery.DeviceRef | None:
    """The just-paired Apple TV by its ``_remotepairing._tcp`` advert."""
    from pymobiledevice3.bonjour import browse_remotepairing
    from pymobiledevice3.pair_records import iter_remote_pair_records_by_identifier
    from pymobiledevice3.remote.tunnel_service import _match_remote_pair_record

    alt_irks = {i: r["peer_alt_irk"] for i, _p, r in iter_remote_pair_records_by_identifier()
                if i == identifier and r.get("peer_alt_irk") is not None}
    if not alt_irks:
        return None
    for attempt in range(3):
        for answer in await browse_remotepairing(timeout=timeout):
            if _match_remote_pair_record(answer, alt_irks) == identifier:
                host = discovery._pick_address(answer)
                if host:
                    return discovery.DeviceRef("", discovery.REMOTE, host=host,
                                               port=answer.port, identifier=identifier)
        await asyncio.sleep(1.0)
    return None


async def pair(identifier: str, host: str, port: int, *, name: str = "",
               ask_pin: AskPin, on_step: Callable[[str], None] = lambda m: None
               ) -> registry.KnownDevice:
    """Pairs the Apple TV or Vision Pro at ``host:port`` and remembers it."""
    from pymobiledevice3.exceptions import PairingError, RemotePairingCompletedError

    on_step(_("Connecting to {name} …", name=name or host))
    service = _pin_pairing_class()(identifier, host, port, ask_pin, name or host, on_step)
    try:
        try:
            await service.connect(autopair=True)
        except RemotePairingCompletedError:
            pass            # paired - the record is written
        except PairingError as exc:
            raise DeviceError(_("The device refused the pairing: {error}", error=exc)) from exc
        except (ConnectionError, OSError, asyncio.TimeoutError) as exc:
            raise DeviceError(_("The device cannot be reached: {error}", error=exc)) from exc
    finally:
        await service.close()

    on_step(_("Paired. Asking the device who it is …"))
    ref = await _find_paired(identifier)
    if ref is None:
        raise DeviceError(_(
            "Paired, but the device does not show up in the network afterwards. "
            "Close the pairing screen on the device and try again."))
    return await _learn(ref)


async def _learn(ref: discovery.DeviceRef) -> registry.KnownDevice:
    """Opens the tunnel once and remembers what the device says about itself
    - the status later shows it without building a tunnel."""
    from . import tunnel
    from .connection import get_value

    handle = tunnel.provider_tunnel(tunnel.remote_pairing(ref.identifier, ref.host, ref.port))
    rsd = await handle.open()
    try:
        values = await get_value(rsd)
    finally:
        await handle.close()
    udid = values.get("UniqueDeviceID") or ref.identifier
    dev = registry.remember(
        udid, name=values.get("DeviceName", ""), product_type=values.get("ProductType", ""),
        os_version=values.get("ProductVersion", ""),
        platform=registry.platform_for(values.get("ProductType", ""), values.get("DeviceClass", "")),
        remote_identifier=ref.identifier, last_host=ref.host)
    if discovery.SCANNER is not None:
        discovery.SCANNER.poke()
    return dev
