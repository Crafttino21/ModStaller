"""The IPA store: apps from sources in the AltStore format.

A *source* is a JSON file on the web listing apps with their download URL,
icon, screenshots and versions - the format AltStore, SideStore and many
others use. ModStaller reads it, shows the apps and, on "Install", downloads
the IPA and signs and installs it like any other.
"""
