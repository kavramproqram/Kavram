#!/bin/bash
cd "$(dirname "$0")"
source myenv/bin/activate
QT_QPA_PLATFORM=xcb python3 Core.py
