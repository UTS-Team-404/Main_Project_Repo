#!/bin/bash
# ========================================
# System Initialization Script
# ========================================
# Checks:
#   - Python 3 presence and version
#   - Python dependencies (requirements.txt)
#   - MySQL installation, service status, and DB setup
#   - Network interfaces & monitor mode status
#   - Run a specified Python script
# Outputs:
#   - Logs to stdout and a logfile (init.log)
# ========================================

LOGFILE="./initLogs/$(date +'%Y-%m-%d_%H:%M:%S').log"
PYTHON_SCRIPT="main.py"       # <-- change this to your script
SQL_FILE="setup.sql"          # <-- change this to your SQL setup file
REQUIREMENTS_FILE="requirements.txt"

# Create or clear log
: > "$LOGFILE"

# Function to log both to file and stdout
log() {
    echo -e "$@" | tee -a "$LOGFILE"
}

# Timestamp
log "\n===== Initialization started at $(date) =====\n"

# --- Check for Python 3 ---
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 -V 2>&1)
    log "[+] Python found: $PY_VERSION"
else
    log "[!] Python3 is not installed. Please install it and re-run this script."
    exit 1
fi

# --- Check Python version compatibility ---
REQUIRED_VERSION="3.8"
if python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"; then
    log "[+] Python version >= $REQUIRED_VERSION OK"
else
    log "[!] Python version too old. Please upgrade to $REQUIRED_VERSION+"
    exit 1
fi

# --- Check for requirements.txt and install ---
if [ -f "$REQUIREMENTS_FILE" ]; then
    log "[*] Checking Python dependencies..."
    python3 -m pip install -r "$REQUIREMENTS_FILE" 2>&1 | tee -a "$LOGFILE"
else
    log "[!] No requirements.txt found — skipping dependency check."
fi

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
    mysql -u root -p < "$SQL_FILE" 2>&1 | tee -a "$LOGFILE"
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

# --- Run the Python script ---
if [ -f "$PYTHON_SCRIPT" ]; then
    log "\n[*] Running Python script: $PYTHON_SCRIPT"
    python3 "$PYTHON_SCRIPT" 2>&1 | tee -a "$LOGFILE"
else
    log "[!] Python script '$PYTHON_SCRIPT' not found. Skipping execution."
fi

log "\n===== Initialization completed at $(date) =====\n"
