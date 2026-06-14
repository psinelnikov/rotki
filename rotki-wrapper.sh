#!/bin/bash
# Wrapper script to run rotkehlchen with proper Python path

# Add venv site-packages to PYTHONPATH
export PYTHONPATH="/opt/rotki/.venv/lib/python3.11/site-packages:$PYTHONPATH"

# Run rotkehlchen using system python
exec /usr/bin/python3 -c '
import sys
sys.path.insert(0, "/opt/rotki")
from rotkehlchen.__main__ import main
main()
' "$@"
