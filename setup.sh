#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Steam Stats Agent Setup ===${NC}"
echo "Setting up your environment..."

# Check for Python 3
if command -v python3 &>/dev/null; then
    echo -e "${GREEN}✓${NC} Python 3 is installed"
    PYTHON_CMD="python3"
else
    echo -e "${RED}✗${NC} Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check for pip
if $PYTHON_CMD -m pip --version &>/dev/null; then
    echo -e "${GREEN}✓${NC} pip is installed"
else
    echo -e "${RED}✗${NC} pip is not installed. Please install pip and try again."
    exit 1
fi

# Create virtual environment
echo "Creating Python virtual environment..."
$PYTHON_CMD -m venv .venv
if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} Failed to create virtual environment. Please check your Python installation."
    exit 1
fi
echo -e "${GREEN}✓${NC} Virtual environment created"

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} Failed to activate virtual environment."
    exit 1
fi
echo -e "${GREEN}✓${NC} Virtual environment activated"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} Failed to install dependencies."
    exit 1
fi
echo -e "${GREEN}✓${NC} Dependencies installed"

# Check for AWS credentials
if [ -f ~/.aws/credentials ]; then
    echo -e "${GREEN}✓${NC} AWS credentials found"
else
    echo -e "${YELLOW}!${NC} AWS credentials not found. Please set up your AWS credentials using 'aws configure'"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo -e "${GREEN}✓${NC} Created .env file"
    echo -e "${YELLOW}!${NC} Please edit the .env file and add your Steam API key"
else
    echo -e "${GREEN}✓${NC} .env file already exists"
fi

echo -e "\n${GREEN}=== Setup Complete ===${NC}"
echo -e "To run the Steam Stats Agent:"
echo -e "1. Make sure your virtual environment is activated: ${YELLOW}source .venv/bin/activate${NC}"
echo -e "2. Get a Steam API key from ${YELLOW}https://steamcommunity.com/dev/apikey${NC}"
echo -e "3. Add your Steam API key to the .env file"
echo -e "4. Run the agent: ${YELLOW}python run.py${NC}"
echo -e "\nEnjoy analyzing your Steam library!"
