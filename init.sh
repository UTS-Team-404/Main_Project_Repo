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

VENV_DIR=".venv"
LOGFILE="./initLogs/$(date +'%Y-%m-%d_%H:%M:%S').log"
PYTHON_SCRIPT="./app/app.py"       # <-- change this to your script
SQL_FILE="setup.sql"          # <-- change this to your SQL setup file
REQUIREMENTS_FILE="requirements.txt"

APT_PACKAGES=(
    python3-gi
    python3-gi-cairo
    gir1.2-gtk-3.0
    libgirepository1.0-dev
    libcairo2-dev
    pkg-config
    python3-dev
    libgtk-3-dev
    build-essential
)

# Create or clear log
: > "$LOGFILE"

# Function to log both to file and stdout
log() {
    echo -e "$@" | tee -a "$LOGFILE"
}

# Timestamp
log "\n===== Initialization started at $(date) =====\n"

# --- Check for sudo/root ---
if [ "$EUID" -ne 0 ]; then
    log "[!] Please run this script with sudo or as root."
    exit 1
fi
log "[+] Running with root privileges."


log "\n[*] Installing required system packages..."
apt install -y "${APT_PACKAGES[@]}" 2>&1 | tee -a "$LOGFILE"
if [ $? -eq 0 ]; then
    log "[+] System packages installed successfully."
else
    log "[X] Some packages failed to install. Check log for details."
fi


# --- Find base user (who invoked sudo) ---
BASE_USER=${SUDO_USER:-$USER}
BASE_HOME=$(eval echo "~$BASE_USER")

log "[*] Script executed by: $BASE_USER"


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

# --- Check for venv module ---
if ! python3 -m venv --help &>/dev/null; then
    log "[!] The 'venv' module is not available in your Python installation."
    exit 1
fi

# --- Create virtual environment if missing ---
if [ ! -d "$VENV_DIR" ]; then
    log "[*] Creating Python virtual environment in $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        log "[X] Failed to create virtual environment."
        exit 1
    fi
else
    log "[+] Virtual environment already exists ($VENV_DIR)"
fi

# --- Activate the venv ---
log "[*] Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# --- Upgrade pip ---
log "[*] Upgrading pip inside venv..."
pip install --upgrade pip 2>&1 | tee -a "$LOGFILE"

# --- Install requirements ---
if [ -f "$REQUIREMENTS_FILE" ]; then
    log "[*] Installing Python dependencies from $REQUIREMENTS_FILE ..."
    pip install -r "$REQUIREMENTS_FILE" 2>&1 | tee -a "$LOGFILE"
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
    log "\n[*] Running Python script: $PYTHON_SCRIPT"
    ./.venv/bin/python3 "$PYTHON_SCRIPT" 2>&1
else
    log "[!] Python script '$PYTHON_SCRIPT' not found. Skipping execution."
fi

