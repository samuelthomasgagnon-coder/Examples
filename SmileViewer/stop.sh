#!/bin/bash

# Stop script for the full-stack application
echo "Stopping all servers..."

# Graceful-then-force killer helpers
kill_port_graceful() {
  PORT=$1
  NAME=$2
  PIDS=$(lsof -ti:"$PORT")
  if [ -z "$PIDS" ]; then
    echo "No process on port $PORT ($NAME)"
    return 0
  fi
  echo "Sending SIGTERM to processes on port $PORT ($NAME)..."
  echo "$PIDS" | xargs kill -TERM 2>/dev/null || true
  # wait up to ~3s for graceful exit
  for i in 1 2 3; do
    sleep 1
    REMAINING=$(lsof -ti:"$PORT")
    [ -z "$REMAINING" ] && break
  done
  REMAINING=$(lsof -ti:"$PORT")
  if [ -n "$REMAINING" ]; then
    echo "Forcing kill (-9) on remaining processes on port $PORT..."
    echo "$REMAINING" | xargs kill -9 2>/dev/null || true
  fi
}

# Kill servers on ports 3000 and 8000 (graceful, then force)
kill_port_graceful 3000 frontend
kill_port_graceful 8000 backend

echo "All servers stopped!"
