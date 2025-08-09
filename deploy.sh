#!/bin/bash

# Telegram Mirror Bot VPS Deployment Script
# For Ubuntu/Debian based systems

set -e

echo "====================================="
echo "  Telegram Mirror Bot Deployment"
echo "====================================="

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
echo "Installing Python..."
sudo apt install -y python3 python3-pip python3-venv

# Install system dependencies
echo "Installing system dependencies..."
sudo apt install -y git screen tmux htop

# Create bot directory
BOT_DIR="/home/$USER/crowbot"
echo "Setting up bot directory at $BOT_DIR..."
mkdir -p $BOT_DIR
cd $BOT_DIR

# Copy bot files (if not already present)
if [ ! -f "bot/main.py" ]; then
    echo "Bot files not found. Please upload the bot files first."
    echo "Expected structure:"
    echo "  $BOT_DIR/bot/*.py"
    echo "  $BOT_DIR/requirements.txt"
    exit 1
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create data directory
mkdir -p data

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/crowbot.service > /dev/null <<EOF
[Unit]
Description=Telegram Mirror Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin"
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/bot/main.py
Restart=always
RestartSec=10
StandardOutput=append:$BOT_DIR/data/bot.log
StandardError=append:$BOT_DIR/data/error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Create start script
cat > start.sh <<'EOF'
#!/bin/bash
cd /home/$USER/crowbot
source venv/bin/activate
python bot/main.py
EOF
chmod +x start.sh

# Create screen start script
cat > start_screen.sh <<'EOF'
#!/bin/bash
screen -dmS crowbot bash -c "cd /home/$USER/crowbot && source venv/bin/activate && python bot/main.py"
echo "Bot started in screen session 'crowbot'"
echo "Use 'screen -r crowbot' to attach"
EOF
chmod +x start_screen.sh

# Create update script
cat > update.sh <<'EOF'
#!/bin/bash
cd /home/$USER/crowbot
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart crowbot
echo "Bot updated and restarted"
EOF
chmod +x update.sh

echo ""
echo "====================================="
echo "  Deployment Complete!"
echo "====================================="
echo ""
echo "Next steps:"
echo "1. Edit data/settings.json with your configuration"
echo "2. Add your session string"
echo ""
echo "To run the bot:"
echo "  Option 1 (systemd): sudo systemctl start crowbot"
echo "  Option 2 (screen):  ./start_screen.sh"
echo "  Option 3 (direct):  ./start.sh"
echo ""
echo "Systemd commands:"
echo "  Start:   sudo systemctl start crowbot"
echo "  Stop:    sudo systemctl stop crowbot"
echo "  Status:  sudo systemctl status crowbot"
echo "  Logs:    sudo journalctl -u crowbot -f"
echo "  Enable:  sudo systemctl enable crowbot"
echo ""
echo "Screen commands:"
echo "  Attach:  screen -r crowbot"
echo "  Detach:  Ctrl+A, D"
echo "  List:    screen -ls"
echo ""