#!/bin/bash

# Load the .env file if it exists
if [ -f .env ]; then
  source .env
fi

# Loading environmental variables from .env, and mission critical defaults in case it isn't found
LOCAL_PORT=${LOCAL_PORT:-3456}
DESTINATION_API=${DESTINATION_API:-"http://localhost:1234"}
ENDPOINT_COMPLETIONS=${ENDPOINT_COMPLETIONS:-"/v1/chat/completions"}
ENDPOINT_MODELS=${ENDPOINT_MODELS:-"/v1/models"}
API_KEYS=${API_KEYS:-""}
WAN_ENABLED=${WAN_ENABLED:-false}
AUTOSTYLE=${AUTOSTYLE:-true}
SYSTEM_MSG=${SYSTEM_MSG:-"You are a helpful AI."}
SYSTEM_OVERRIDE=${SYSTEM_OVERRIDE:-false}
USE_TMUX=false
RELOAD=false

VENV_DIR="venv"

PYTHON_BIN=$(which python3 || echo "python3")

# Check if Python is available
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo "Python 3 is not installed or not in PATH. Please install Python 3 or provide the path to Python 3."
    exit 1
fi

# Check if the virtual environment directory exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON_BIN -m venv "$VENV_DIR"
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Install or update dependencies
echo "Installing/Updating dependencies..."
pip install fastapi uvicorn httpx pytz pydantic python-dotenv

UVICORN_BIN=$(which uvicorn || echo "uvicorn")
TMUX_BIN=$(which tmux || echo "tmux")

# Parse command-line options
while [ "$#" -gt 0 ]; do
  case "$1" in
    --port)
      LOCAL_PORT="$2"
      shift 2
      ;;
    --api-url)
      DESTINATION_API="$2"
      shift 2
      ;;
    --sys)
      SYSTEM_MSG="$2"
      shift 2
      ;;
    --forcesys)
      SYSTEM_OVERRIDE=true
      shift
      ;;
    --tmux)
      USE_TMUX=true
      shift
      ;;
    --wan)
      WAN_ENABLED=true
      shift
      ;;
    --nostyle)
      AUTOSTYLE=false
      shift
      ;;
    --reload)
      RELOAD=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Export the environment variables
export DESTINATION_API
export SYSTEM_MSG
export SYSTEM_OVERRIDE
export AUTOSTYLE

# Build the command to launch Uvicorn
COMMAND="/opt/homebrew/bin/python3.11 -m uvicorn BananaPhone:api --port $LOCAL_PORT"

# If WAN is enabled, modify the command
if [ "$WAN_ENABLED" = true ]; then
  COMMAND="$COMMAND --host 0.0.0.0"
fi

# If reload is requested, modify the command
if [ "$RELOAD" = true ]; then
  COMMAND="$COMMAND --reload"
fi

# If tmux is requested, modify the command
if [ "$USE_TMUX" = true ]; then
  COMMAND="tmux new-session -d -s BananaPhone '$COMMAND'"
fi

# Execute the command
eval $COMMAND
