#!/bin/bash
######################################################################################################################
# Install the sms-to-shell script as a Systemd service
# For Ubuntu / Debian / Raspbian
# David Harrop
# May 2023
#######################################################################################################################

# Set variables
SERVICE_NAME="sms-to-shell"
SERVICE_DESCR="SMS to shell service"
SERVICE_FILE="/lib/systemd/system/$SERVICE_NAME.service"
INSTALL_DIR="/opt/$SERVICE_NAME"
PYTHON_SCRIPT="sms-to-shell.py"
SHELL_USER="root" # Commands will run in this user context.

# Create installation directory
sudo mkdir -p $INSTALL_DIR

# Copy Python script to installation directory
sudo cp $PYTHON_SCRIPT $INSTALL_DIR

# Create systemd service file
sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=$SERVICE_DESCR
After=multi-user.target

[Service]
ExecStart=/usr/bin/python3 $INSTALL_DIR/$PYTHON_SCRIPT
WorkingDirectory=$INSTALL_DIR
Restart=always
RestartSec=5
User=$SHELL_USER

[Install]
WantedBy=multi-user.target
EOF

# Set permissions for the service file
sudo chmod 644 $SERVICE_FILE

# Reload systemd configuration
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

# Wait for the service to start
echo "Waiting for the service to start..."
sleep 5

# Check the service status
SERVICE_STATUS=$(systemctl is-active $SERVICE_NAME)
if [ "$SERVICE_STATUS" = "active" ]; then
    echo "Service $SERVICE_NAME is running."
else
    echo "Failed to start the service. Check the status using 'systemctl status $SERVICE_NAME'."
fi

