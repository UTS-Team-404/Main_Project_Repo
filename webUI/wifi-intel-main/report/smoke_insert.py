#!/usr/bin/env python3
# tools/smoke_insert.py  (name can stay the same)
#
# Purpose:
#  - Start a project in Harry's DB and print its PID (default).
#  - Optionally seed ONE demo row (only if you pass --seed).
#  - Optionally STOP an existing project by PID (with --stop PID).
#
# This never alters schema. It uses your safe client wrapper.

from datetime import datetime
import argparse
from client.ingest_client import (
    create_project,
    insert_sniff_external,
    stop_project,
)

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    ap = argparse.ArgumentParser(
        description="Start/stop (and optionally seed) projects in Harry's DB."
    )
    ap.add_argument(
        "--seed",
        action="store_true",
        help="Also insert one demo external row (off by default).",
    )
    ap.add_argument(
        "--stop",
        type=int,
        metavar="PID",
        help="Stop an existing project ID by setting stopTime=now.",
    )
    args = ap.parse_args()

    # Stop mode: don't start anything new
    if args.stop:
        stop_project(args.stop, now_str())
        print(f"Stopped project {args.stop}.")
        return

    # Default: START a new external-sniff project and print PID
    pid = create_project(now_str(), "sniff_external")
    print(f"ProjectID: {pid}  (open)")

    # Optional seed (only if explicitly requested)
    if args.seed:
        insert_sniff_external(
            project_id=pid,
            capture_time=now_str(),
            src_mac="aa:bb:cc:dd:ee:ff",
            dst_mac="ff:ee:dd:cc:bb:aa",
            ssid="TestSSID",
            enc_type="WPA2",     # must be one of Public/WPA/WPA2/WPA3 or None
            auth_mode="PSK",     # PSK or Enterprise or None
            strength=-48,
            content_length=0,
            type_external="Broadcast",
        )
        print(f"Seeded 1 demo row into project {pid}.")

    print("Leave this project open while your real capture runs (Kali sniffer).")
    print("When finished, stop it with:  python smoke_insert.py --stop", pid)

if __name__ == "__main__":
    main()
