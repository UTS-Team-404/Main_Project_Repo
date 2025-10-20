# Integrated-Web-UI-main/web/gen_report.py
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

# --- locate sibling repo "wifi-intel-main" so we can import your reporting code
WEB_DIR = Path(__file__).resolve().parent
ROOT = WEB_DIR.parent                              # Integrated-Web-UI-main
WIFI = ROOT.parent / "wifi-intel-main"            # adjust if your layout differs
sys.path.insert(0, str(WIFI))

# --- import your PDF builder + DB helpers from wifi-intel-main
from report.generate_report import build_pdf
from report.db_adapter import (
    connect_db,
    fetch_project_metadata,
    fetch_ingest_as_analysis_df,
    latest_project_id,
)
from reportlab.lib.pagesizes import A4, landscape

# DB creds (same as Harry)
# DB_HOST = "127.0.0.1"
# DB_USER = "team404user"
# DB_PASS = "pass"
# DB_NAME = "team404"
import os
DB_HOST = os.getenv("TEAM404_DB_HOST", "127.0.0.1")
DB_USER = os.getenv("TEAM404_DB_USER", "team404user")
DB_PASS = os.getenv("TEAM404_DB_PASS", "pass")
DB_NAME = os.getenv("TEAM404_DB_NAME", "team404")



def generate_wifi_pdf(
    project_id: str | int = "latest",
    ssid_filter: str = "",
    mac_mask_mode: str = "none",     # accepted but not used yet; kept for future-proofing
) -> Path:
    """Generate the professional Wi-Fi PDF and return the file path."""
    # connect
    conn = connect_db(DB_HOST, DB_USER, DB_PASS, DB_NAME)

    # resolve project id
    if str(project_id).lower() in {"latest", "last"}:
        pid = latest_project_id(conn)
        if pid is None:
            raise RuntimeError("No projects found in DB.")
    else:
        pid = int(project_id)

    # fetch data + metadata
    project_meta = fetch_project_metadata(conn, pid)
    df = fetch_ingest_as_analysis_df(conn, pid)

    # optional SSID filter if present
    if ssid_filter:
        ssid_col = "SSID" if "SSID" in df.columns else ("ssid" if "ssid" in df.columns else None)
        if ssid_col:
            df = df[df[ssid_col] == ssid_filter].copy()

    # write into /static/reports so Flask can serve it
    out_dir = WEB_DIR / "static" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_pdf = out_dir / f"{pid}-sniff_external-{stamp}.pdf"

    # include the logo if available
    logo_guess = WIFI / "assets" / "y404_logo.png"
    logo_path = str(logo_guess) if logo_guess.exists() else None

    # metadata for your PDF
    meta = {
        "title": "Team 404 – Wi-Fi Intel",
        "project": f"DB Run (Project {pid})",
        "subtitle": "Prototype",
        "filter_ssid": ssid_filter,
        "app_version": "0.1.0",
        "project_meta": project_meta,
        "data_file_name": "(database)",
        "capture_mode": "monitor",
        "logo_path": logo_path,
        "logo_align": "right",
        "logo_max_width_mm": 60.0,
        "logo_max_height_mm": 22.0,
        "logo_upscale": False,
        "pagesize": landscape(A4),   # DB reports look better landscape
    }

    # build the PDF using your reporting code
    build_pdf(df, out_pdf, meta, source="db")
    return out_pdf
