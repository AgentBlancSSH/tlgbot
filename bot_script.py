#!/bin/bash

# Function to print colored messages
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RESET="\033[0m"

print_colored() {
    echo -e "${2}${1}${RESET}"
}

# Update the system
print_colored "Updating the system..." $BLUE
sudo apt-get update && sudo apt-get upgrade -y || { print_colored "System update failed." $RED; exit 1; }

# Check if Python3 and pip3 are installed
print_colored "Checking for Python3 and pip..." $BLUE
if ! command -v python3 &> /dev/null; then
    print_colored "Python3 is not installed. Installing..." $YELLOW
    sudo apt-get install python3 -y || { print_colored "Python3 installation failed." $RED; exit 1; }
else
    print_colored "Python3 is already installed." $GREEN
fi

if ! command -v pip3 &> /dev/null; then
    print_colored "pip3 is not installed. Installing..." $YELLOW
    sudo apt-get install python3-pip -y || { print_colored "pip3 installation failed." $RED; exit 1; }
else
    print_colored "pip3 is already installed." $GREEN
fi

# Create a virtual environment
print_colored "Creating the virtual environment..." $BLUE
python3 -m venv venv || { print_colored "Failed to create virtual environment." $RED; exit 1; }
source venv/bin/activate

# Check and create the .env file
if [ ! -f .env ]; then
    print_colored "The .env file is missing. Please enter your Telegram bot token to create the .env file." $YELLOW
    read -sp "Enter your Telegram bot token: " API_TOKEN_E
    echo

    # Validate the token by making a request to Telegram API
    response=$(curl -s https://api.telegram.org/bot${API_TOKEN_E}/getMe)
    if echo "$response" | grep -q '"ok":true'; then
        echo "API_TOKEN_E=$API_TOKEN_E" > .env
        print_colored ".env file created successfully." $GREEN
    else
        print_colored "Invalid Telegram bot token. Please check and try again." $RED
        exit 1
    fi
else
    print_colored ".env file already exists." $GREEN
fi

# Check for the requirements.txt file and create it if missing
if [ ! -f requirements.txt ]; then
    print_colored "requirements.txt is missing. Creating a default requirements.txt file." $YELLOW
    cat <<EOF > requirements.txt
pyTelegramBotAPI==4.11.0
python-dotenv==0.19.2
EOF
    print_colored "requirements.txt created with default dependencies." $GREEN
fi

# Install Python dependencies
print_colored "Installing Python dependencies..." $BLUE
pip install -r requirements.txt || { print_colored "Failed to install Python dependencies." $RED; deactivate; exit 1; }

# Initialize the database
print_colored "Initializing the database..." $BLUE
python3 -c "
import sqlite3
conn = sqlite3.connect('ptcfrance.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    address TEXT,
    postal_code TEXT,
    email TEXT,
    phone TEXT
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    dosage REAL,
    price REAL
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product_id INTEGER,
    quantity INTEGER
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS order_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    status TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()
conn.close()
" || { print_colored "Database initialization failed." $RED; deactivate; exit 1; }

# Start the bot
print_colored "Starting the bot..." $BLUE
python3 bot_script.py || { print_colored "Failed to start the bot." $RED; deactivate; exit 1; }

print_colored "The setup and run script executed successfully." $GREEN
