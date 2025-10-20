#!/etc/.venv/python3


import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from threading import Lock
from queue import Queue

# Scapy
from scapy.all import sniff, RadioTap, Dot11, Dot11Elt, IP, TCP, UDP

# MySQL
import mysql.connector
from mysql.connector import Error

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'team404user',
    'password': 'pass',
    'database': 'team404'
}

# Global queue for database writes
db_queue = Queue()
_gps_lat = None
_gps_lon = None
_gps_lock = Lock()

# little helpy functions

def run_quiet(cmd):
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def set_monitor(iface):
    run_quiet(["ip", "link", "set", iface, "down"])
    run_quiet(["iw", "dev", iface, "set", "type", "monitor"])
    run_quiet(["ip", "link", "set", iface, "up"])
    time.sleep(0.2)

def set_managed(iface):
    run_quiet(["ip", "link", "set", iface, "down"])
    run_quiet(["iw", "dev", iface, "set", "type", "managed"])
    run_quiet(["ip", "link", "set", iface, "up"])
    time.sleep(0.2)

def rssi_from(pkt):
    try:
        if hasattr(pkt, "dBm_AntSignal") and pkt.dBm_AntSignal is not None:
            return int(pkt.dBm_AntSignal)
        rt = pkt.getlayer(RadioTap)
        if rt and "dBm_AntSignal" in rt.fields and rt.fields["dBm_AntSignal"] is not None:
            return int(rt.fields["dBm_AntSignal"])
    except Exception:
        pass
    return None

def ssid_from(pkt):
    try:
        elt = pkt.getlayer(Dot11Elt, ID=0)  # SSID element
        if elt and elt.info is not None:
            ssid = elt.info.decode("utf-8", errors="ignore")
            return ssid if ssid else None
    except Exception:
        pass
    return None

def ip_ports(pkt):
    if pkt.haslayer(IP):
        ip = pkt[IP]
        src = getattr(ip, "src", None)
        dst = getattr(ip, "dst", None)
        sp = dp = None
        if pkt.haslayer(TCP):
            sp, dp = pkt[TCP].sport, pkt[TCP].dport
        elif pkt.haslayer(UDP):
            sp, dp = pkt[UDP].sport, pkt[UDP].dport
        return src, dst, sp, dp
    return None, None, None, None

def get_encryption_info(pkt):
    """
    Extract encryption and auth info from beacon/probe response frames.
    Returns (encType, authMode) matching DB constraints.
    """
    try:
        if pkt.haslayer(Dot11Elt):
            cap = getattr(pkt, "cap", None)
            if cap and "privacy" in str(cap).lower():
                # Look for RSN/WPA information elements
                elt = pkt.getlayer(Dot11Elt)
                while elt:
                    if elt.ID == 48:  # RSN IE (WPA2/WPA3)
                        # Check for WPA3 (SAE)
                        try:
                            info = bytes(elt.info)
                            if b'\x00\x0f\xac\x08' in info:  # SAE AKM
                                return "WPA3", "Enterprise"
                            elif b'\x00\x0f\xac\x02' in info:  # PSK
                                return "WPA2", "PSK"
                            elif b'\x00\x0f\xac\x01' in info:  # 802.1X
                                return "WPA2", "Enterprise"
                        except:
                            pass
                        return "WPA2", "PSK"
                    elif elt.ID == 221:  # Vendor specific (WPA)
                        try:
                            info = bytes(elt.info)
                            if b'\x00\x50\xf2' in info[:3]:  # Microsoft WPA OUI
                                if b'\x00\x50\xf2\x02' in info:  # PSK
                                    return "WPA", "PSK"
                                elif b'\x00\x50\xf2\x01' in info:  # 802.1X
                                    return "WPA", "Enterprise"
                        except:
                            pass
                        return "WPA", "PSK"
                    elt = elt.payload.getlayer(Dot11Elt)
                # If privacy bit set but no WPA/WPA2, assume WEP (treat as Public for DB)
                return "Public", None
            else:
                return "Public", None
    except Exception:
        pass
    return None, None

# GPS 

def gps_thread():
    """
    Keep _gps_lat/_gps_lon updated once per second.
    Prefer gpsd Python API; fall back to gpspipe.
    Works with gpsd fed by your phone over UDP.
    """
    global _gps_lat, _gps_lon
    # Try gpsd Python API first
    session = None
    try:
        from gps import gps, WATCH_ENABLE, WATCH_NEWSTYLE
        session = gps(mode=WATCH_ENABLE | WATCH_NEWSTYLE)
    except Exception:
        session = None

    if session is not None:
        # gpsd-py3 path
        while True:
            try:
                report = session.next()
                if report and getattr(report, 'class', None) == 'TPV':
                    lat = getattr(report, 'lat', None)
                    lon = getattr(report, 'lon', None)
                    with _gps_lock:
                        _gps_lat = float(lat) if lat is not None else None
                        _gps_lon = float(lon) if lon is not None else None
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(0.25)
            time.sleep(0.2)
    else:
        # Fallback to gpspipe polling
        while True:
            try:
                out = subprocess.check_output(
                    ["gpspipe", "-w", "-n", "1"],
                    text=True, stderr=subprocess.DEVNULL
                )
                lat = lon = None
                for line in out.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("class") == "TPV":
                        lat = obj.get("lat")
                        lon = obj.get("lon")
                with _gps_lock:
                    _gps_lat = float(lat) if lat is not None else None
                    _gps_lon = float(lon) if lon is not None else None
            except KeyboardInterrupt:
                break
            except Exception:
                with _gps_lock:
                    _gps_lat = None
                    _gps_lon = None
            time.sleep(1.0)

def create_project(connection):
    """
    Create a new project in ProjectDB with projectType='sniff_internal'.
    Returns the new project ID.
    """
    try:
        cursor = connection.cursor()
        insert_query = """
        INSERT INTO ProjectDB (startTime, projectType)
        VALUES (%s, 'sniff_internal')
        """
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(insert_query, (start_time,))
        connection.commit()
        project_id = cursor.lastrowid
        cursor.close()
        print(f"[+] Created new project with ID: {project_id}")
        return project_id
    except Error as e:
        print(f"[!] Failed to create project: {e}", file=sys.stderr)
        sys.exit(1)

def update_project_stop_time(connection, project_id):
    """
    Update the stopTime for a project when capture ends.
    """
    try:
        cursor = connection.cursor()
        update_query = """
        UPDATE ProjectDB SET stopTime = %s WHERE ID = %s
        """
        stop_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(update_query, (stop_time, project_id))
        connection.commit()
        cursor.close()
        print(f"[+] Updated project {project_id} stop time")
    except Error as e:
        print(f"[!] Failed to update project stop time: {e}", file=sys.stderr)

# Database writer thread

def db_writer_thread(project_id):
    """
    Continuously pull entries from db_queue and write to MySQL.
    """
    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("[*] Connected to MySQL database")
            cursor = connection.cursor()
            
            insert_query = """
            INSERT INTO IngestDB 
            (projectID, captureTime, srcMac, dstMac, SSID, encType, authMode, 
             gpsLat, gpsLong, strength, contentLength, typeExternal, typeInternal,
             srcIP, dstIP, srcPort, dstPort, sniffType)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            while True:
                entry = db_queue.get()
                if entry is None:  # Poison pill to stop thread
                    break
                    
                try:
                    cursor.execute(insert_query, entry)
                    connection.commit()
                except Error as e:
                    print(f"[!] Database error: {e}", file=sys.stderr)
                    # Try to reconnect
                    try:
                        if not connection.is_connected():
                            connection.reconnect()
                            cursor = connection.cursor()
                    except:
                        pass
                        
    except Error as e:
        print(f"[!] Failed to connect to database: {e}", file=sys.stderr)
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("[*] Database connection closed")

# Packet processing

def csvq(s):
    """Format value for CSV output"""
    if s is None: return "NULL"
    s = str(s)
    if any(c in s for c in [",", '"', "\n"]):
        s = '"' + s.replace('"', '""') + '"'
    return s

def make_printer(sniff_type_value, project_id):
    """
    Return a function for scapy.sniff(prn=...) that queues entries for database insertion
    and prints CSV to console.
    """
    def prn(pkt):
        if not pkt.haslayer(Dot11):
            return
            
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        src = getattr(pkt, "addr2", None)
        dst = getattr(pkt, "addr1", None)
        ssid = ssid_from(pkt)
        rssi = rssi_from(pkt)
        length = len(pkt) if pkt else 0
        ext = {0: "management", 1: "control", 2: "data"}.get(getattr(pkt, "type", None), "unknown")
        itn = str(getattr(pkt, "subtype", ""))
        ip_src, ip_dst, sp, dp = ip_ports(pkt)
        
        # Extract encryption info
        enc_type, auth_mode = get_encryption_info(pkt)

        with _gps_lock:
            glat = _gps_lat if _gps_lat is not None else None
            glon = _gps_lon if _gps_lon is not None else None

        if not ssid:
            ssid = "(hidden)"
        # Prepare entry tuple matching the INSERT query order
        entry = (
            project_id,      # projectID
            ts,              # captureTime
            src,             # srcMac
            dst,             # dstMac
            ssid,            # SSID
            enc_type,        # encType
            auth_mode,       # authMode
            glat,            # gpsLat
            glon,            # gpsLong
            rssi,            # strength
            length,          # contentLength
            ext,             # typeExternal
            itn,             # typeInternal
            ip_src,          # srcIP
            ip_dst,          # dstIP
            sp,              # srcPort
            dp,              # dstPort
            sniff_type_value # sniffType
        )
        
        # Queue for database insertion
        db_queue.put(entry)
        
        # Print to console as CSV
        csv_row = [
            ts, src, dst, ssid, enc_type, auth_mode,
            glat, glon, rssi, length, ext, itn,
            ip_src, ip_dst, sp, dp, sniff_type_value
        ]
        print(",".join(csvq(x) for x in csv_row), flush=True)
        print(db_queue.qsize())

    return prn

# main

def main():
    if os.geteuid() != 0:
        print("Run with sudo.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Sniff all WiFi traffic and write to MySQL database (with GPS)."
    )
    parser.add_argument("iface", nargs="?", default="wlan1",
                        help="wireless interface (default: wlan1)")
    parser.add_argument("-p", "--project", type=int, default=None,
                        help="Project ID (optional - will create new project if not specified)")
    parser.add_argument("-c", "--channel", type=int, default=None,
                        help="set specific channel (optional, omit to scan all channels)")
    parser.add_argument("--host", default="localhost",
                        help="MySQL host (default: localhost)")
    parser.add_argument("--user", default="root",
                        help="MySQL user (default: root)")
    parser.add_argument("--password", default="",
                        help="MySQL password")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--internal", action="store_true",
                       help="set sniffType to 'internal'")
    group.add_argument("-e", "--external", action="store_true",
                       help="set sniffType to 'external'")
    args = parser.parse_args()

    iface = args.iface
    project_id = args.project
    sniff_type_value = "internal" if (args.internal or not args.external) else "external"

    # Create or use existing project
    try:
        temp_conn = mysql.connector.connect(**DB_CONFIG)
        if temp_conn.is_connected():
            if project_id is None:
                # Create new project
                project_id = create_project(temp_conn)
            else:
                print(f"[*] Using existing project ID: {project_id}")
            temp_conn.close()
        else:
            print("[!] Failed to connect to database", file=sys.stderr)
            sys.exit(1)
    except Error as e:
        print(f"[!] Database connection error: {e}", file=sys.stderr)
        sys.exit(1)

    # Set monitor mode
    print(f"[*] Setting {iface} to monitor mode...")
    set_monitor(iface)
    
    # Set channel if specified
    if args.channel:
        print(f"[*] Setting channel to {args.channel}")
        run_quiet(["iw", "dev", iface, "set", "channel", str(args.channel)])
        time.sleep(0.2)
    else:
        print("[*] Scanning all channels (no specific channel set)")

    # Start GPS thread
    print("[*] Starting GPS thread...")
    threading.Thread(target=gps_thread, daemon=True).start()

    # Start database writer thread
    print("[*] Starting database writer thread...")
    db_thread = threading.Thread(target=db_writer_thread, args=(project_id,), daemon=True)
    db_thread.start()

    # Print CSV header
    header = [
        "captureTime", "srcMac", "dstMac", "SSID", "encType", "authMode",
        "gpsLat", "gpsLong", "strength", "contentLength", "typeExternal", "typeInternal",
        "srcIP", "dstIP", "srcPort", "dstPort", "sniffType"
    ]
    print(",".join(header), flush=True)

    # Live sniff with Scapy (until Ctrl+C)
    print(f"[*] Starting capture on {iface} for project {project_id}... (Press Ctrl+C to stop)")
    try:
        sniff(iface=iface, prn=make_printer(sniff_type_value, project_id), store=False)
    except KeyboardInterrupt:
        print("\n[*] Stopping capture...")
        # Send poison pill to stop db thread
        db_queue.put(None)
        db_thread.join(timeout=5)
        
        # Update project stop time
        try:
            temp_conn = mysql.connector.connect(**DB_CONFIG)
            if temp_conn.is_connected():
                update_project_stop_time(temp_conn, project_id)
                temp_conn.close()
        except Error as e:
            print(f"[!] Failed to update project stop time: {e}", file=sys.stderr)
    finally:
        # Leave managed for convenience
        set_managed(iface)
        print("[*] Done.")

if __name__ == "__main__":
    main()
