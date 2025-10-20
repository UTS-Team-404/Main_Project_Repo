# 🛰️ Team 404 – Integrated Wi-Fi Intel System

This repository combines the **three core modules** of the Team 404 Capstone Project:

| Folder | Component | Description |
|:-------|:-----------|:-------------|
| `wifi-intel-main/` | Automated Reporting | Generates analytical PDF reports using Python, ReportLab, Pandas, and Matplotlib. |
| `database-main/` | Database & Ingestion | Contains SQL schemas, data ingestion scripts, and MySQL/MariaDB adapters. |
| `Integrated-Web-UI-main/` | Web Interface | Web dashboard that connects the DB and allows users to view live analytics and generate reports. |

---

## 🚀 Quick Start

### 1. Clone the Repository
Clone this repository into your local workspace (or the Kali/Windows system used for development):

```bash

Run Guide (Windows & Linux)

This repository contains three pieces:
team404-integrated/
├─ wifi-intel-main/          # Python report generator (PDFs, charts)
├─ database-main/            # SQL schema + sample data
└─ Integrated-Web-UI-main/   # Web UI (Flask) to drive reports/visualize

1) Prerequisites

Python 3.10–3.12 (python --version)

Git

MariaDB or MySQL 8+ (for DB mode). CSV mode works without a database.

Tip: On Windows, prefer mysql-connector-python (already in requirements) to avoid compiler headaches.

2) Quick Start — CSV mode (no database)

This proves your pipeline works end-to-end.

Windows (PowerShell)
cd wifi-intel-main
python -m venv .venv
# if activation is blocked once: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run with a CSV
python -m report.generate_report `
  --csv data/samples/wifi_sample.csv `
  --out out/WiFi_Report_CSV.pdf


Linux (bash)
cd wifi-intel-main
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run with a CSV
python -m report.generate_report \
  --csv data/samples/wifi_sample.csv \
  --out out/WiFi_Report_CSV.pdf

3) Database mode (MariaDB/MySQL)
3.1 Install & start the DB
Windows

Install MariaDB Server (MSI). Keep port=3306.

In my.ini, ensure: [mysqld]
default_authentication_plugin = mysql_native_password

Start MariaDB from Services app or MariaDB Tray.

Open a client (HeidiSQL / MySQL Shell / PowerShell):
SHOW VARIABLES LIKE 'version';
SHOW VARIABLES LIKE 'default_authentication_plugin'; -- expect mysql_native_password


Linux:
sudo apt update
sudo apt install -y mariadb-server
sudo systemctl enable --now mariadb
sudo mysql_secure_installation


3.2 Create database & user, load schema

From repo root:
# Either use the mysql client on Windows or Linux
mysql -u root -p -e "CREATE DATABASE team404 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE USER 'team404user'@'%' IDENTIFIED BY 'pass';"
mysql -u root -p -e "GRANT ALL PRIVILEGES ON team404.* TO 'team404user'@'%'; FLUSH PRIVILEGES;"

# Load schema and (optional) sample data
mysql -u team404user -p team404 < database-main/schema.sql
# optional
mysql -u team404user -p team404 < database-main/seed_sample.sql



3.3 App config (.env)

In wifi-intel-main/, create .env (copy from .env.example if present):
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=team404
DB_USER=team404user
DB_PASS=pass
# Optional: override connector (defaults are fine)
DB_DRIVER=mysql-connector

3.4 Run the report (DB mode)
Windows (PowerShell):
cd wifi-intel-main
.\.venv\Scripts\Activate.ps1
python -m report.generate_report --project-id 1 --out out/WiFi_Report_DB_1.pdf


Linux (bash):
cd wifi-intel-main
source .venv/bin/activate
python -m report.generate_report --project-id 1 --out out/WiFi_Report_DB_1.pdf

--project-id is the integer your team uses to group a capture session.

The script pulls rows from DB → builds the same analytics as CSV mode (frames/min timeline, RSSI stats, encType × authMode matrix, MAC table, etc.).

4) Web UI

The UI lives in Integrated-Web-UI-main/ and wraps the same report engine.

Install & run
Windows (PowerShell)
cd Integrated-Web-UI-main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Copy env
Copy-Item .env.example .env
# Edit DB_* values to match the database above

# Start (common options below—use the one that matches your file names)
# If the entrypoint is app.py:
python app.py
# OR Flask style:
$env:FLASK_APP="app" ; flask run --debug

Linux (bash)
cd Integrated-Web-UI-main
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit DB_* values

# Start
python app.py
# OR:
export FLASK_APP=app
flask run --debug


Browse to http://127.0.0.1:5000/. Tabs include Wi-Fi Report and Heat Map. When the DB has data for the selected project_id, the UI triggers the same PDF build and/or renders charts inline.

Not sure which module name to run?
Look for the Python file that creates the Flask app (search for Flask( or create_app).
PowerShell: gci -r -Filter *.py | sls -Pattern "Flask\(" -List
Linux: grep -R "Flask(" -n .

5) Typical workflow

Import or capture data → rows land in team404 DB under your project_id.

Run DB mode to generate the assessment-ready PDF.

For dry-runs or demos without DB access, run CSV mode with a sample file.

6) Troubleshooting

Cannot activate venv on Windows: run once in the same PowerShell window
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

DB connect error: verify with a raw SQL ping
mysql -u team404user -ppass -h 127.0.0.1 -P 3306 -D team404 -e "SELECT 1;"

Auth plugin mismatch: SHOW VARIABLES LIKE 'default_authentication_plugin'; must be mysql_native_password.

Matplotlib headless errors on Linux: the code already uses the Agg backend; make sure you’re inside the venv you installed to.

PDF not showing encType/authMode: your CSV/DB rows must include those columns/fields; the report shows them only when present (auto-gated to avoid empty tables).git clone https://github.com/UTS-Team-404/team404-integrated.git
cd team404-integrated
