#!/bin/bash
echo "Starting UmbrellaOS..."

kill -9 $(lsof -t -i:8765) 2>/dev/null
kill -9 $(lsof -t -i:3000) 2>/dev/null
sleep 2

cd /workspaces/UmbrellaOS/files/umbrella-core
python -m uvicorn main:app --host 0.0.0.0 --port 8765 --reload > /tmp/backend.log 2>&1 &
echo "Waiting for backend..."
sleep 6
tail -5 /tmp/backend.log

cd /workspaces/UmbrellaOS/Dashboard
pnpm dev > /tmp/dashboard.log 2>&1 &
echo "Waiting for dashboard..."
sleep 5
tail -5 /tmp/dashboard.log

cd /workspaces/UmbrellaOS/discord-bot
python main.py > /tmp/bot.log 2>&1 &
echo "Waiting for bot..."
sleep 3
tail -5 /tmp/bot.log

echo "All services started!"
