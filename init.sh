#!/bin/bash
# ========================================
# System Initialization Script
# ========================================
# Checks:
#   - Python 3 presence and version
#   - checks and creates venv 
#   - Python dependencies (requirements.txt)
#   - MySQL installation, service status, and DB setup
#   - Network interfaces & monitor mode status
#   - Run a specified Python script
# Outputs:
#   - Logs to stdout and a logfile (init.log)
# ========================================

VENV_DIR="/etc/.venv"
LOGFILE="/etc/initLogs/$(date +'%Y-%m-%d_%H:%M:%S').log"
PYTHON_SCRIPT="/etc/Main_Project_Repo/app/app.py"       # <-- change this to your script
WEBPYTHON_SCRIPT= "/etc/Main_Project_Repo/webUI/Integrated-Web-UI-main/web/app.py"
SQL_FILE="/etc/Main_Project_Repo/setup.sql"          # <-- change this to your SQL setup file
INTERFACE="wlan1"

# Create or clear log
sudo : > "$LOGFILE"

# Function to log both to file and stdout
log() {
    sudo echo -e "$@" | tee -a "$LOGFILE"
}

# Timestamp
log "\n===== Initialization started at $(date) =====\n"

# --- Check for sudo/root ---
if [ "$EUID" -ne 0 ]; then
    log "[!] Please run this script with sudo or as root."
    exit 1
fi
log "[+] Running with root privileges."


# --- Find base user (who invoked sudo) ---
BASE_USER=${SUDO_USER:-$USER}
BASE_HOME=$(eval echo "~$BASE_USER")

log "[*] Script executed by: $BASE_USER"


# --- Activate the venv ---
log "[*] Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# --- Check MySQL installation ---
if command -v mysql &>/dev/null; then
    log "[+] MySQL client found."
else
    log "[!] MySQL is not installed. Please install it (apt install mysql-server)."
    exit 1
fi

# --- Check MySQL service status ---
if systemctl is-active --quiet mysql; then
    log "[+] MySQL service is running."
else
    log "[!] MySQL service not running. Attempting to start..."
    sudo systemctl start mysql
    if systemctl is-active --quiet mysql; then
        log "[+] MySQL service started successfully."
    else
        log "[X] Failed to start MySQL service."
        exit 1
    fi
fi

# --- Run SQL setup file ---
if [ -f "$SQL_FILE" ]; then
    log "[*] Running SQL setup from $SQL_FILE ..."
    mysql < "$SQL_FILE" 2>&1 | tee -a "$LOGFILE"
else
    log "[!] SQL setup file '$SQL_FILE' not found."
fi

# --- Network interface status ---
log "\n[*] Checking network interfaces..."
ip link show | tee -a "$LOGFILE"

# --- Check for monitor mode ---
log "\n[*] Checking monitor mode interfaces..."
if command -v iwconfig &>/dev/null; then
    iwconfig 2>/dev/null | grep -E "Mode:Monitor|IEEE" | tee -a "$LOGFILE"
else
    log "[!] iwconfig not found — skipping monitor mode check."
fi

# --- Log Wi-Fi connections ---
log "\n[*] Active Wi-Fi connections:"
nmcli dev wifi list 2>/dev/null | tee -a "$LOGFILE"


log "\n===== Initialization completed at $(date) =====\n"

# --- Run the Python script ---
if [ -f "$PYTHON_SCRIPT" ]; then
    log "\n[*] Starting Reports Hotspot Webserver UI: /etc/Main_Project_Repo/web/Integrated-Web-UI-main/web/app.py in background..."
    sudo $VENV_DIR/bin/python3 /etc/Main_Project_Repo/web/Integrated-Web-UI-main/web/app.py & 
    WEB_PID=$!
    log "[+] On screen Web UI started successfully (PID: $WEB_PID)"
    sudo $VENV_DIR/bin/python3 /etc/Main_Project_Repo/scan/scan.py -i $INTERFACE & 
    SCAN_PID=$!
    log "[+] Scanner started successfully (PID: $SCAN_PID)"
    log "\n[*] Running Python script: $PYTHON_SCRIPT"
    sudo $VENV_DIR/bin/python3 "$PYTHON_SCRIPT" --no-sandbox 2>&1
else
    log "[!] Python script '$PYTHON_SCRIPT' not found. Skipping execution."
fi

