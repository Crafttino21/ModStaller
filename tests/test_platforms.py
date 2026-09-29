"""Which IPA may go on which device - iPhone, iPad, iPod touch, Apple TV,
Vision Pro."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from modstaller.apple import devservices
from modstaller.device.connection import DeviceInfo
from modstaller.pipeline import incompatibility
from modstaller.signing.ipa import device_families, platform_of


def _dev(product, platform="ios"):
    return DeviceInfo(udid="X", name="D", product_type=product, ios_version="18.0",
                      build="B", developer_mode=True, platform=platform)


def _ipa(platform="ios", families=(1, 2)):
    return SimpleNamespace(platform=platform, device_families=list(families))


@pytest.mark.parametrize("info, platform", [
    ({"CFBundleSupportedPlatforms": ["XROS"]}, "xros"),
    ({"UIDeviceFamily": [7]}, "xros"),
    ({"DTPlatformName": "xros"}, "xros"),
    ({"CFBundleSupportedPlatforms": ["iPhoneOS"], "UIDeviceFamily": [1, 2]}, "ios"),
])
def test_vision_pro_ipas_are_recognised(info, platform):
    assert platform_of(info) == platform


def test_device_families_are_read_robustly():
    assert device_families({"UIDeviceFamily": [2, 1, 1]}) == [1, 2]
    assert device_families({"UIDeviceFamily": 2}) == [2]
    assert device_families({"UIDeviceFamily": ["x", 1]}) == [1]
    assert device_families({}) == []


@pytest.mark.parametrize("ipa, device, allowed", [
    # iPhone apps run on an iPad in compatibility mode.
    (_ipa(families=[1]), _dev("iPad16,3"), True),
    # iPad-only apps do not start on an iPhone or iPod touch.
    (_ipa(families=[2]), _dev("iPhone17,2"), False),
    (_ipa(families=[2]), _dev("iPod9,1"), False),
    (_ipa(families=[2]), _dev("iPad16,3"), True),
    (_ipa(families=[1, 2]), _dev("iPod9,1"), True),
    # visionOS runs iPhone/iPad apps ("Designed for iPad") ...
    (_ipa(), _dev("RealityDevice14,1", "xros"), True),
    (_ipa("xros", [7]), _dev("RealityDevice14,1", "xros"), True),
    # ... but its own apps only run there.
    (_ipa("xros", [7]), _dev("iPad16,3"), False),
    (_ipa("xros", [7]), _dev("AppleTV14,1", "tvos"), False),
    # The Apple TV stays strict.
    (_ipa(), _dev("AppleTV14,1", "tvos"), False),
    (_ipa("tvos", [3]), _dev("iPhone17,2"), False),
])
def test_what_may_go_where(ipa, device, allowed):
    assert (incompatibility(ipa, device) is None) is allowed


def test_an_ipad_only_app_names_the_device():
    text = incompatibility(_ipa(families=[2]), _dev("iPod9,1"))
    assert "iPad" in text and "iPod touch" in text


def test_the_vision_pro_signs_the_ios_way_for_now():
    assert devservices._platform_params("xros") == {}
    assert devservices._platform_params("tvos")["DTDK_Platform"] == "tvos"
    # A copy - changing it must not change the table.
    devservices._platform_params("tvos")["x"] = "y"
    assert "x" not in devservices._platform_params("tvos")
