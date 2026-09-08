"""Compatibility stub for Android builds.

pymavlink treats fastcrc as optional at runtime and falls back to its
pure-Python CRC implementation when fastcrc.crc16.mcrf4xx is unavailable.
"""
