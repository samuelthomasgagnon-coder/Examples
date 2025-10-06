#!/bin/bash

echo "Setting up WebRTC Smile Detection Application..."

# Create and activate virtual environment
echo "Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies in virtual environment..."
pip install -r requirements.txt

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

# Make scripts executable
echo "Making scripts executable..."
chmod +x stop.sh

echo "Setup complete!"
echo ""
echo "Virtual environment created at: .venv/"
echo ""
echo "To start the application:"
echo "  npm run start"
echo ""
echo "To stop the application:"
echo "  npm run stop"
echo ""
echo "To manually activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "The application will be available at:"
echo "  Frontend: http://localhost:3000"
echo "  Backend: http://localhost:8000"
