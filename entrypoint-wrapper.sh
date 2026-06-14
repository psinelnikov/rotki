#!/bin/bash
# Wrapper to create rotki symlink before starting

# Create the rotki executable directly
cat > /usr/sbin/rotki << 'PYTHON_EOF'
#!/opt/rotki/.venv/bin/python
import sys
sys.path.insert(0, "/opt/rotki")
from rotkehlchen.__main__ import main
main()
PYTHON_EOF

chmod +x /usr/sbin/rotki

exec /opt/rotki/entrypoint.py
