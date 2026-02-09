#!/bin/bash
# Script to start the Karma backend server locally
# Kills any existing backend processes and starts a fresh server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the project root directory (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo -e "${GREEN}🚀 Starting Karma Backend${NC}"
echo "Project root: $PROJECT_ROOT"
echo "Backend directory: $BACKEND_DIR"

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}❌ Error: Backend directory not found at $BACKEND_DIR${NC}"
    exit 1
fi

# Check if virtualenv exists
VENV_DIR="$BACKEND_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  Virtualenv not found at $VENV_DIR${NC}"
    echo -e "${YELLOW}   Creating virtualenv...${NC}"
    cd "$BACKEND_DIR"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtualenv created${NC}"
fi

# Kill any existing backend processes
echo -e "${YELLOW}🔍 Checking for existing backend processes...${NC}"

# Find and kill processes running uvicorn with app.main:app
# Try pgrep first (Linux), fallback to ps + grep (macOS)
if command -v pgrep >/dev/null 2>&1; then
    UVICORN_PIDS=$(pgrep -f "uvicorn.*app.main:app" 2>/dev/null || true)
else
    # macOS fallback: use ps and grep
    UVICORN_PIDS=$(ps aux | grep -i "uvicorn.*app.main:app" | grep -v grep | awk '{print $2}' | tr '\n' ' ' || true)
fi

if [ -n "$UVICORN_PIDS" ]; then
    echo -e "${YELLOW}   Found existing uvicorn processes: $UVICORN_PIDS${NC}"
    echo -e "${YELLOW}   Killing existing processes...${NC}"
    for pid in $UVICORN_PIDS; do
        kill -9 "$pid" 2>/dev/null || true
    done
    sleep 1
    echo -e "${GREEN}✅ Killed existing backend processes${NC}"
else
    echo -e "${GREEN}   No existing backend processes found${NC}"
fi

# Also check for processes on port 8000
if command -v lsof >/dev/null 2>&1; then
    PORT_8000_PID=$(lsof -ti:8000 2>/dev/null || true)
    if [ -n "$PORT_8000_PID" ]; then
        echo -e "${YELLOW}   Found process on port 8000: $PORT_8000_PID${NC}"
        echo -e "${YELLOW}   Killing process on port 8000...${NC}"
        kill -9 "$PORT_8000_PID" 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}✅ Freed port 8000${NC}"
    fi
else
    # Fallback: try to find process using netstat or ss
    if command -v netstat >/dev/null 2>&1; then
        PORT_8000_PID=$(netstat -tulpn 2>/dev/null | grep :8000 | awk '{print $7}' | cut -d'/' -f1 | head -1 || true)
        if [ -n "$PORT_8000_PID" ]; then
            echo -e "${YELLOW}   Found process on port 8000: $PORT_8000_PID${NC}"
            kill -9 "$PORT_8000_PID" 2>/dev/null || true
            sleep 1
            echo -e "${GREEN}✅ Freed port 8000${NC}"
        fi
    fi
fi

# Activate virtualenv
echo -e "${GREEN}📦 Activating virtualenv...${NC}"
source "$VENV_DIR/bin/activate"

# Check if requirements are installed
if ! python -c "import uvicorn" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Dependencies not installed. Installing requirements...${NC}"
    cd "$BACKEND_DIR"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
fi

# Change to backend directory
cd "$BACKEND_DIR"

# Start the backend server
echo -e "${GREEN}🚀 Starting backend server on http://localhost:8000${NC}"
echo -e "${GREEN}   API docs: http://localhost:8000/docs${NC}"
echo -e "${GREEN}   Health check: http://localhost:8000/api/health${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start uvicorn with reload for development
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
