# client/ingest_client.py
# Your safe, team-aligned DB client (do not touch Harry's files).
# Reads connection settings from env vars so the team can override per machine.

from datetime import datetime
from pathlib import Path
import os
import mysql.connector

DB_CONFIG = {
    "host": os.getenv("TEAM404_DB_HOST", "127.0.0.1"),   # set to Kali IP when needed
    "port": int(os.getenv("TEAM404_DB_PORT", "3306")),
    "database": os.getenv("TEAM404_DB_NAME", "team404"),
    "user": os.getenv("TEAM404_DB_USER", "team404user"),
    "password": os.getenv("TEAM404_DB_PASS", "pass"),
    "charset": "utf8mb4",
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

# ---------------- ProjectDB ---------------- #

def create_project(start_time: str, project_type: str):
    """
    project_type ∈ {'sniff_external','sniff_internal','heatmap'}
    """
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO ProjectDB (startTime, projectType)
        VALUES (%s, %s)
    """, (start_time, project_type))
    conn.commit()
    pid = cur.lastrowid
    cur.close(); conn.close()
    return pid

def stop_project(project_id: int, stop_time: str):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        UPDATE ProjectDB SET stopTime=%s WHERE ID=%s
    """, (stop_time, project_id))
    conn.commit()
    cur.close(); conn.close()

def get_projects():
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM ProjectDB")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

# ---------------- IngestDB (EXTERNAL/INTERNAL/HEATMAP) ---------------- #

def insert_sniff_external(
    project_id: int,
    capture_time: str,
    src_mac: str,
    dst_mac: str = None,
    ssid: str = None,
    enc_type: str = None,     # Public|WPA|WPA2|WPA3 or None
    auth_mode: str = None,    # PSK|Enterprise or None
    strength: int = None,
    content_length: int = None,
    type_external: str = None # e.g. "Broadcast", "DataFrame", etc.
):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO IngestDB (
            projectID, captureTime, srcMac, dstMac, SSID, encType, authMode,
            strength, contentLength, typeExternal, sniffType
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'external')
    """, (project_id, capture_time, src_mac, dst_mac, ssid, enc_type, auth_mode,
          strength, content_length, type_external))
    conn.commit()
    iid = cur.lastrowid
    cur.close(); conn.close()
    return iid

def insert_sniff_internal(
    project_id: int,
    capture_time: str,
    src_mac: str,
    dst_mac: str = None,
    ssid: str = None,
    enc_type: str = None,
    auth_mode: str = None,
    strength: int = None,
    content_length: int = None,
    type_internal: str = None, # e.g. TCP/UDP/HTTP/DNS
    src_ip: str = None,
    dst_ip: str = None,
    src_port: int = None,      # 0..65535 or None
    dst_port: int = None,      # 0..65535 or None
    sniff_type: str = "internal"
):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO IngestDB (
            projectID, captureTime, srcMac, dstMac, SSID, encType, authMode,
            strength, contentLength, typeInternal, srcIP, dstIP, srcPort, dstPort, sniffType
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (project_id, capture_time, src_mac, dst_mac, ssid, enc_type, auth_mode,
          strength, content_length, type_internal, src_ip, dst_ip, src_port, dst_port, sniff_type))
    conn.commit()
    iid = cur.lastrowid
    cur.close(); conn.close()
    return iid

def insert_heatmap(
    project_id: int,
    capture_time: str,
    src_mac: str,
    ssid: str = None,
    gps_lat: float = None,   # schema stores INT; we cast below
    gps_long: float = None,
    strength: int = None,
):
    conn = get_connection(); cur = conn.cursor()
    lat = int(gps_lat) if gps_lat is not None else None
    lng = int(gps_long) if gps_long is not None else None
    cur.execute("""
        INSERT INTO IngestDB (
            projectID, captureTime, srcMac, SSID, gpsLat, gpsLong, strength
        ) VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (project_id, capture_time, src_mac, ssid, lat, lng, strength))
    conn.commit()
    iid = cur.lastrowid
    cur.close(); conn.close()
    return iid

def get_ingests_by_project(project_id: int):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM IngestDB WHERE projectID=%s", (project_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_ingests_by_mac(mac: str):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM IngestDB WHERE srcMac=%s OR dstMac=%s", (mac, mac))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def get_table_schema(table_name: str):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
    """, (DB_CONFIG["database"], table_name))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows
