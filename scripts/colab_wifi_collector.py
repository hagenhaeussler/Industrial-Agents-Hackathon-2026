#!/usr/bin/env python3
"""Opt-in Wi-Fi scan bridge. Default: print JSON locally; nothing is uploaded.

Requires no Python third-party package for Android Termux / Linux iw / JSON.
macOS optionally uses a separately installed, permission-enabled CoreWLAN bridge.
Never changes Wi-Fi settings, enables monitoring mode, or invokes sudo.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def termux_scan(rows: object, *, boottime_s: float, observed_at: str, max_age_s: float = 20) -> dict:
    """Translate cached Android ScanResult times (microseconds since boot)."""
    if not isinstance(rows, list):
        raise ValueError('Termux returned an error; grant Termux:API precise location and enable Location/Wi-Fi')
    readings = []
    dropped = 0
    for row in rows:
        try:
            stamp = float(row['timestamp']) / 1_000_000
            age = boottime_s - stamp
            rssi = float(row['rssi'])
            if stamp <= 0 or not math.isfinite(age) or age < -.5 or age > max_age_s:
                dropped += 1
                continue
            readings.append({'bssid': row['bssid'], 'rssi_dbm': rssi, 'age_s': round(max(0, age), 3)})
        except (KeyError, TypeError, ValueError):
            dropped += 1
    return {'observed_at': observed_at, 'readings': readings, 'synthetic': False,
            'collector': 'termux_cached_scan', 'dropped_old_or_invalid': dropped}


def iw_scan(output: str, *, observed_at: str, max_age_s: float = 20) -> dict:
    readings = []
    for block in re.split(r'(?m)^BSS ', output)[1:]:
        bssid = re.match(r'([0-9a-fA-F:]{17})', block)
        signal = re.search(r'(?m)^\s*signal:\s*(-?\d+(?:\.\d+)?)\s*dBm', block)
        age_match = re.search(r'(?m)^\s*last seen:\s*(\d+)\s*ms ago', block)
        # Refuse entries without a known measurement age; receipt time is not
        # sufficient evidence that the kernel's cached BSS entry is current.
        if not bssid or not signal or not age_match:
            continue
        age = int(age_match[1]) / 1000
        if age <= max_age_s:
            readings.append({'bssid': bssid[1].lower(), 'rssi_dbm': float(signal[1]), 'age_s': age})
    return {'observed_at': observed_at, 'readings': readings, 'synthetic': False, 'collector': 'linux_iw_scan'}


def capture(source: str, *, input_path: str | None = None, interface: str = 'wlan0') -> dict:
    if source == 'file':
        if not input_path:
            raise ValueError('--input is required for --source file')
        content = Path(input_path).read_text() if input_path != '-' else sys.stdin.read()
        if len(content) > 256_000:
            raise ValueError('scan JSON exceeds 256 KB')
        scan = json.loads(content)
        if not isinstance(scan, dict) or 'observed_at' not in scan or 'readings' not in scan:
            raise ValueError('input must be a scan object with original observed_at and readings')
        return scan  # Preserve age and synthetic flag; never refresh a recording.
    if source == 'termux':
        completed = subprocess.run(['termux-wifi-scaninfo'], check=True, text=True, capture_output=True, timeout=20)
        if not hasattr(time, 'CLOCK_BOOTTIME'):
            raise ValueError('CLOCK_BOOTTIME is unavailable; cannot prove Android scan freshness')
        return termux_scan(json.loads(completed.stdout), boottime_s=time.clock_gettime(time.CLOCK_BOOTTIME), observed_at=utc_now())
    if source == 'linux-iw':
        if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,32}', interface):
            raise ValueError('invalid wireless interface name')
        completed = subprocess.run(['iw', 'dev', interface, 'scan'], check=True, text=True, capture_output=True, timeout=25)
        return iw_scan(completed.stdout, observed_at=utc_now())
    if source == 'macos':
        try:
            import CoreWLAN  # optional PyObjC, not a project dependency
        except ImportError as exc:
            raise ValueError('macOS requires an installed CoreWLAN/PyObjC bridge and approved Location access; use Android if unavailable') from exc
        wifi = CoreWLAN.CWWiFiClient.sharedWiFiClient().interface()
        if wifi is None:
            raise ValueError('No macOS Wi-Fi interface is available')
        networks, error = wifi.scanForNetworksWithName_error_(None, None)
        if error is not None:
            raise ValueError('CoreWLAN scan failed; check app/Location permissions')
        readings = [{'bssid': item.bssid(), 'rssi_dbm': item.rssiValue(), 'age_s': 0}
                    for item in (networks or []) if item.bssid()]
        if not readings:
            raise ValueError('CoreWLAN returned no visible BSSIDs, possibly redacted; no fallback measurements invented')
        return {'observed_at': utc_now(), 'readings': readings, 'synthetic': False, 'collector': 'macos_corewlan_scan'}
    raise ValueError('unknown scan source')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('redirect refused; use the final trusted endpoint URL')


def send_scan(endpoint: str, token: str, device_id: str, label: str, scan: dict) -> int:
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.username or parsed.password or parsed.fragment or parsed.query:
        raise ValueError('endpoint must not contain credentials, query or fragment')
    local = parsed.hostname in {'localhost', '127.0.0.1', '::1'}
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and local):
        raise ValueError('remote endpoint must use HTTPS; HTTP is allowed only for loopback testing')
    if not token or '\n' in token or '\r' in token:
        raise ValueError('COLAB_TRACKING_TOKEN must contain a valid pairing token')
    body = json.dumps({'device_id': device_id, 'label': label, 'scan': scan}, allow_nan=False).encode()
    request = urllib.request.Request(endpoint, body, {'Content-Type': 'application/json', 'X-Colab-Token': token}, method='POST')
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=15) as response:
        return response.status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=['termux', 'linux-iw', 'macos', 'file'], required=True)
    parser.add_argument('--input', help='scan JSON for file source; - reads stdin, original timestamp preserved')
    parser.add_argument('--interface', default='wlan0')
    parser.add_argument('--output', help='append local scan objects as JSONL; use count=1 for a JSON object')
    parser.add_argument('--endpoint', help='explicit opt-in HTTPS scan upload endpoint; absent means capture only')
    parser.add_argument('--device-id', default=None, help='stable pseudonymous identifier; random if omitted')
    parser.add_argument('--label', default='Demo Android')
    parser.add_argument('--count', type=int, default=1, help='finite number of captures (default 1)')
    parser.add_argument('--interval', type=float, default=30, help='seconds between captures; does not force Android to scan')
    args = parser.parse_args(argv)
    if not 1 <= args.count <= 1000 or not math.isfinite(args.interval) or args.interval < 1:
        parser.error('count must be 1..1000 and interval at least one second')
    if args.source == 'file' and args.count != 1:
        parser.error('file replay is single-shot; it never advances the recording timestamp')
    device_id = args.device_id or 'wifi-' + uuid.uuid4().hex[:12]
    token = os.environ.get('COLAB_TRACKING_TOKEN', '')
    if args.endpoint and not token:
        parser.error('set COLAB_TRACKING_TOKEN from the pairing flow; never use the admin token')
    try:
        for iteration in range(args.count):
            scan = capture(args.source, input_path=args.input, interface=args.interface)
            encoded = json.dumps(scan, allow_nan=False)
            if args.output:
                with open(args.output, 'a', encoding='utf-8') as handle:
                    handle.write(encoded + '\n')
            else:
                print(encoded, flush=True)
            if args.endpoint:
                status = send_scan(args.endpoint, token, device_id, args.label, scan)
                print(f'HTTP {status}; device={device_id}; readings={len(scan["readings"])}', file=sys.stderr)
            if iteration + 1 < args.count:
                time.sleep(args.interval)
    except (ValueError, OSError, subprocess.SubprocessError, urllib.error.URLError) as exc:
        # Neither the bearer token nor provider stderr is printed.
        print(f'Collection/upload unavailable: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
