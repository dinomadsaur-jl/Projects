#!/bin/bash

# Complete automated XML modifier with systemd timer
# Usage: ./auto_xml_mod.sh <filename.xml> <search_pattern> <lines_to_add>

# Color codes (will auto-disable if not in terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; NC=''
fi

# Log file
LOG_FILE="/var/log/xml-modifier.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Function to log messages
log_message() {
    echo "[$TIMESTAMP] $1" >> "$LOG_FILE"
    echo -e "$1"
}

# Function to check if running as root (for systemd operations)
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        log_message "${YELLOW}Note: Some operations may need sudo. You may be prompted for password.${NC}"
    fi
}

# Function to create the revert script
create_revert_script() {
    local script_path="/usr/local/bin/xml-reverter"
    
    if [ ! -f "$script_path" ]; then
        log_message "${YELLOW}Creating revert script...${NC}"
        sudo tee "$script_path" > /dev/null << 'EOF'
#!/bin/bash
# Auto-generated XML revert script
BACKUP_FILE="$1"
XML_FILE="$2"
LOG_FILE="/var/log/xml-modifier.log"

echo "[$(date)] Starting revert process" >> "$LOG_FILE"

if [ -f "$BACKUP_FILE" ]; then
    if cp "$BACKUP_FILE" "$XML_FILE" 2>/dev/null; then
        echo "[$(date)] SUCCESS: Reverted $XML_FILE from $BACKUP_FILE" >> "$LOG_FILE"
        echo "Revert completed successfully at $(date)"
        # Clean up old backups (keep last 5)
        ls -t "${XML_FILE}.backup."* 2>/dev/null | tail -n +6 | xargs -r rm
    else
        echo "[$(date)] ERROR: Failed to copy backup to $XML_FILE" >> "$LOG_FILE"
        exit 1
    fi
else
    echo "[$(date)] ERROR: Backup file $BACKUP_FILE not found!" >> "$LOG_FILE"
    exit 1
fi
EOF
        sudo chmod +x "$script_path"
        log_message "${GREEN}✓ Revert script created${NC}"
    fi
}

# Function to clean up old timers
cleanup_old_timers() {
    local file_pattern="$1"
    log_message "${YELLOW}Cleaning up old timers for this file...${NC}"
    
    # Find and disable old timers for this file
    for timer in $(systemctl list-timers --all --no-legend | grep "revert-xml-$(basename "$file_pattern")" | awk '{print $NF}'); do
        sudo systemctl stop "$timer" 2>/dev/null
        sudo systemctl disable "$timer" 2>/dev/null
        sudo rm -f "/etc/systemd/system/$timer" 2>/dev/null
        service_name=$(echo "$timer" | sed 's/.timer/.service/')
        sudo rm -f "/etc/systemd/system/$service_name" 2>/dev/null
    done
    
    sudo systemctl daemon-reload
    log_message "${GREEN}✓ Cleanup complete${NC}"
}

# Main script starts here
if [ $# -ne 3 ]; then
    echo -e "${RED}Usage:${NC} $0 <xml_file> <search_pattern> <lines_to_add>"
    echo "Example: $0 config.xml '<configuration>' '<new_element>value</new_element>'"
    exit 1
fi

XML_FILE="$1"
SEARCH_PATTERN="$2"
LINES_TO_ADD="$3"

# Get absolute path
if command -v realpath &> /dev/null; then
    XML_FILE_ABS=$(realpath "$XML_FILE" 2>/dev/null)
else
    XML_FILE_ABS=$(readlink -f "$XML_FILE" 2>/dev/null)
fi

# Validate inputs
if [ ! -f "$XML_FILE_ABS" ]; then
    echo -e "${RED}Error:${NC} File '$XML_FILE' not found!"
    exit 1
fi

if ! grep -q "$SEARCH_PATTERN" "$XML_FILE_ABS"; then
    echo -e "${RED}Error:${NC} Pattern '$SEARCH_PATTERN' not found in file!"
    exit 1
fi

# Check if systemd is available
if ! command -v systemctl &> /dev/null; then
    echo -e "${RED}Error:${NC} systemd not found on this system!"
    exit 1
fi

# Create log directory if it doesn't exist
sudo mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null
sudo touch "$LOG_FILE" 2>/dev/null
sudo chmod 666 "$LOG_FILE" 2>/dev/null

# Initialize logging
log_message "${BLUE}══════════════════════════════════════════════════════════════${NC}"
log_message "${GREEN}Starting automated XML modification${NC}"
log_message "${BLUE}══════════════════════════════════════════════════════════════${NC}"

# Step 1: Create revert script if needed
create_revert_script

# Step 2: Clean up old timers for this file
cleanup_old_timers "$XML_FILE_ABS"

# Step 3: Generate unique names
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${XML_FILE_ABS}.backup.${TIMESTAMP}"
SAFE_NAME=$(basename "$XML_FILE_ABS" | sed 's/[^a-zA-Z0-9]/-/g')
TIMER_NAME="revert-${SAFE_NAME}-${TIMESTAMP}.timer"
SERVICE_NAME="revert-${SAFE_NAME}-${TIMESTAMP}.service"

# Step 4: Create backup
log_message "${YELLOW}Creating backup...${NC}"
if cp "$XML_FILE_ABS" "$BACKUP_FILE"; then
    log_message "${GREEN}✓ Backup created: $BACKUP_FILE${NC}"
else
    log_message "${RED}✗ Backup failed!${NC}"
    exit 1
fi

# Step 5: Modify file
log_message "${YELLOW}Modifying file...${NC}"
TEMP_FILE="${XML_FILE_ABS}.tmp"
ESCAPED_LINES=$(echo "$LINES_TO_ADD" | sed 's/[\/&]/\\&/g')

if sed "/$SEARCH_PATTERN/a\\
$ESCAPED_LINES
" "$XML_FILE_ABS" > "$TEMP_FILE" 2>/dev/null; then
    if mv "$TEMP_FILE" "$XML_FILE_ABS" 2>/dev/null; then
        log_message "${GREEN}✓ File modified successfully${NC}"
    else
        log_message "${RED}✗ Failed to replace file!${NC}"
        rm -f "$TEMP_FILE"
        exit 1
    fi
else
    log_message "${RED}✗ Modification failed!${NC}"
    rm -f "$TEMP_FILE"
    exit 1
fi

# Step 6: Create service file
log_message "${YELLOW}Creating systemd service...${NC}"
sudo tee "/etc/systemd/system/$SERVICE_NAME" > /dev/null << EOF
[Unit]
Description=Auto-revert for $(basename "$XML_FILE_ABS")
After=network.target
Before=shutdown.target reboot.target halt.target
Requires=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/xml-reverter "$BACKUP_FILE" "$XML_FILE_ABS"
User=root
Group=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

if [ $? -eq 0 ]; then
    log_message "${GREEN}✓ Service created${NC}"
else
    log_message "${RED}✗ Service creation failed!${NC}"
    exit 1
fi

# Step 7: Create timer file
log_message "${YELLOW}Creating systemd timer...${NC}"
REVERT_TIME=$(date -d '+1 hour' '+%Y-%m-%d %H:%M:%S')
sudo tee "/etc/systemd/system/$TIMER_NAME" > /dev/null << EOF
[Unit]
Description=Revert $(basename "$XML_FILE_ABS") at $REVERT_TIME
Requires=$SERVICE_NAME

[Timer]
OnActiveSec=1h
Persistent=true
WakeSystem=false

[Install]
WantedBy=timers.target
EOF

if [ $? -eq 0 ]; then
    log_message "${GREEN}✓ Timer created${NC}"
else
    log_message "${RED}✗ Timer creation failed!${NC}"
    exit 1
fi

# Step 8: Enable and start timer
log_message "${YELLOW}Activating timer...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable "$TIMER_NAME" > /dev/null 2>&1
sudo systemctl start "$TIMER_NAME" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    log_message "${GREEN}✓ Timer activated${NC}"
else
    log_message "${RED}✗ Timer activation failed!${NC}"
    exit 1
fi

# Step 9: Verify timer is running
sleep 2
if systemctl is-active --quiet "$TIMER_NAME"; then
    log_message "${GREEN}✓ Timer verified running${NC}"
else
    log_message "${YELLOW}⚠ Timer status unknown, but should be scheduled${NC}"
fi

# Step 10: Final status and info
log_message "${GREEN}══════════════════════════════════════════════════════════════${NC}"
log_message "${GREEN}✅ AUTOMATION COMPLETE - EVERYTHING DONE${NC}"
log_message "${GREEN}══════════════════════════════════════════════════════════════${NC}"
log_message "File: $XML_FILE_ABS"
log_message "Backup: $BACKUP_FILE"
log_message "Timer: $TIMER_NAME"
log_message "Revert time: $REVERT_TIME"
log_message "Log file: $LOG_FILE"
log_message "${GREEN}══════════════════════════════════════════════════════════════${NC}"

# Create a status file with all information
STATUS_FILE="/tmp/xml-mod-${TIMESTAMP}.info"
cat > "$STATUS_FILE" << EOF
XML MODIFICATION STATUS
=======================
Date: $(date)
File: $XML_FILE_ABS
Backup: $BACKUP_FILE
Timer: $TIMER_NAME
Revert scheduled: $REVERT_TIME

Commands:
---------
Check timer: systemctl status $TIMER_NAME
List timers: systemctl list-timers | grep revert
View logs: journalctl -u $SERVICE_NAME -f
Cancel: sudo systemctl stop $TIMER_NAME && sudo systemctl disable $TIMER_NAME
EOF

log_message "Status file saved to: $STATUS_FILE"

# Optional: Show quick status
echo ""
echo -e "${BLUE}Quick status:${NC} systemctl status $TIMER_NAME --no-pager -l"
echo ""

exit 0