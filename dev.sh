#!/bin/bash
# Start backend and frontend dev servers
trap 'kill 0' EXIT

cd "$(dirname "$0")"

# Kill ALL existing processes on our ports
for port in 8001 5173; do
  pids=$(lsof -ti :"$port" 2>/dev/null)
  if [ -n "$pids" ]; then
    echo "Killing processes on port $port: $pids"
    echo "$pids" | xargs kill -9 2>/dev/null
    sleep 1
  fi
done

(cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8001) &
(cd frontend && npm run dev) &

wait
