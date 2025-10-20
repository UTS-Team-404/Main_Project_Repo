# tools/seed_demo.py
from datetime import datetime, timedelta
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import random
from client.ingest_client import create_project, insert_sniff_external, stop_project

def main():
    now = datetime.now()
    pid = create_project(now.strftime("%Y-%m-%d %H:%M:%S"), "sniff_external")
    print(f"ProjectID: {pid}")

    macs = [f"aa:bb:cc:{i:02x}:{i+1:02x}:{i+2:02x}" for i in range(10, 110, 2)]
    ssids = ["UTS-WiFi", "eduroam", "Hidden", "LabNet", "GuestNet"]

    total = 0
    for m in macs:
        for _ in range(random.randint(10, 20)):  # ~1000 rows total
            ts = now + timedelta(seconds=random.randint(0, 300))
            insert_sniff_external(
                project_id=pid,
                capture_time=ts.strftime("%Y-%m-%d %H:%M:%S"),
                src_mac=m,
                dst_mac=None,
                ssid=random.choice(ssids),
                enc_type=random.choice(["WPA2","WPA3","Public"]),
                auth_mode=random.choice(["PSK","Enterprise"]),
                strength=random.randint(-92, -35),
                content_length=random.randint(40, 1500),
                type_external=random.choice(["Beacon","Probe","Broadcast","DataFrame"]),
            )
            total += 1

    stop_project(pid, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(f"Seeded {total} rows and closed project {pid}")

if __name__ == "__main__":
    main()
