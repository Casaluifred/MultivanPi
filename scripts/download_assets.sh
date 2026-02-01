#!/bin/bash
STATIC_DIR="/home/fred/MultivanPi/static"
mkdir -p "$STATIC_DIR"
curl -L -o "$STATIC_DIR/lucide.min.js" "https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"
curl -L -o "$STATIC_DIR/chart.min.js" "https://cdn.jsdelivr.net/npm/chart.js"
