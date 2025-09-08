#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate   # dikkat: "myenv" değil
QT_QPA_PLATFORM=xcb python3 Kavram.py
