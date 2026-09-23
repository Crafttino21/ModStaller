"""Modellname und Bauform fuer das Geraetebild in der Oberflaeche."""

from __future__ import annotations

import pytest

from modstaller.device.connection import Battery, battery
from modstaller.device.models import (
    HOME_BUTTON, IPAD, ISLAND, NOTCH, form_factor, marketing_name,
)


@pytest.mark.parametrize("product, name", [
    ("iPhone17,2", "iPhone 16 Pro Max"),
    ("iPhone9,3", "iPhone 7"),            # "(GSM)" gehoert nicht in die Anzeige
    ("iPhone99,1", "iPhone99,1"),         # unbekannt: lieber roh als falsch
])
def test_marketing_name(product, name):
    assert marketing_name(product) == name


@pytest.mark.parametrize("product, form", [
    ("iPhone10,4", HOME_BUTTON),   # iPhone 8
    ("iPhone10,3", NOTCH),         # iPhone X
    ("iPhone12,8", HOME_BUTTON),   # SE 2 - neue Nummer, altes Gehaeuse
    ("iPhone14,7", NOTCH),         # iPhone 14
    ("iPhone15,2", ISLAND),        # iPhone 14 Pro
    ("iPhone17,5", NOTCH),         # iPhone 16e
    ("iPhone18,4", ISLAND),        # iPhone Air
    ("iPad13,1", IPAD),
])
def test_form_factor(product, form):
    assert form_factor(product) == form


class Lockdown:
    def __init__(self, values):
        self.values = values

    async def get_value(self, domain=None, key=None):
        assert domain == "com.apple.mobile.battery"
        if isinstance(self.values, Exception):
            raise self.values
        return self.values


async def test_battery_reads_level_and_charging():
    got = await battery(Lockdown({"BatteryCurrentCapacity": 87,
                                  "BatteryIsCharging": True}))
    assert got == Battery(level=87, charging=True)


async def test_battery_is_optional():
    assert await battery(Lockdown(RuntimeError("nope"))) is None
    assert await battery(Lockdown({})) is None
