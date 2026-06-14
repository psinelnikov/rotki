#!/usr/bin/python3
"""Modified entrypoint for self-hosted AGPL version that works with venv Python."""
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from signal import SIGINT, SIGQUIT, SIGTERM
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger('monitor')
logging.basicConfig(level=logging.DEBUG)

DEFAULT_LOG_LEVEL = 'critical'

def check_core_api_availability(retries: int = 30, wait_seconds: int = 10) -> bool:
    attempt = 0
    while attempt < retries:
        try:
            request = Request('http://localhost:4242/api/1/ping')
            with urlopen(request, timeout=10) as response:
                if response.status == 200:
                    logger.info(f'Ping successful at attempt {attempt + 1}')
                    return True
        except HTTPError as e:
            logger.error(f'Ping failed, HTTP error: {e.reason}')
        except URLError as e:
            logger.error(f'Ping failed, URL error: {e.reason}')
        except Exception as e:
            logger.error(f'Ping failed: {e}')
        
        attempt += 1
        time.sleep(wait_seconds)
    
    return False

def load_config() -> tuple[list[str], str]:
    config_file = Path('/config/rotki_config.json')
    if not config_file.exists():
        logger.info('No config file, using defaults')
        return [], DEFAULT_LOG_LEVEL
    
    try:
        with open(config_file) as f:
            config = json.load(f)
        log_level = config.get('loglevel', DEFAULT_LOG_LEVEL)
        return config.get('api_args', []), log_level
    except Exception as e:
        logger.error(f'Error loading config: {e}')
        return [], DEFAULT_LOG_LEVEL

def main() -> None:
    config_args, log_level = load_config()
    
    # Use the wrapper script
    base_args = [
        '/usr/sbin/rotki',
        '--rest-api-port', '4242',
        '--api-cors', 'http://localhost:*/*,app://localhost/*',
        '--host', '0.0.0.0',
        '--data-dir', '/data',
        '--logfile', '/logs/rotki.log',
        '--loglevel', log_level,
    ]
    
    cmd = [str(arg) for arg in (base_args + config_args)]
    logger.info(f'Starting rotki backend: {cmd}')
    
    rotki = subprocess.Popen(cmd)
    
    if rotki.returncode == 1:
        logger.error('Failed to start rotki')
        sys.exit(1)
    
    if check_core_api_availability() is False:
        logger.error('API did not become available')
        rotki.terminate()
        sys.exit(1)
    
    # Start colibri
    colibri_cmd = [
        '/opt/rotki/colibri',
        '--database', '/data/global.db',
        '--port', '4343',
        '--api-cors=http://localhost:*/*,app://localhost/*',
    ]
    colibri = subprocess.Popen(colibri_cmd)
    
    if colibri.returncode == 1:
        logger.error('Failed to start colibri')
        rotki.terminate()
        sys.exit(1)
    
    # Start nginx
    logger.info('Starting nginx')
    nginx = subprocess.Popen('nginx -g "daemon off;"', shell=True)
    
    if nginx.returncode == 1:
        logger.error('Failed to start nginx')
        rotki.terminate()
        colibri.terminate()
        sys.exit(1)
    
    def graceful_exit(received_signal: int, _frame: Any) -> None:
        logger.info(f'Received signal {received_signal}. Exiting')
        for proc, name in [(colibri, 'colibri'), (rotki, 'rotki'), (nginx, 'nginx')]:
            if proc.poll() is None:
                proc.terminate()
        sys.exit(0)
    
    signal.signal(SIGINT, graceful_exit)
    signal.signal(SIGTERM, graceful_exit)
    signal.signal(SIGQUIT, graceful_exit)
    
    while True:
        time.sleep(60)
        
        if rotki.poll() is not None:
            logger.error('rotki has terminated, exiting')
            sys.exit(1)
        
        if nginx.poll() is not None:
            logger.error('nginx has terminated, exiting')
            sys.exit(1)

if __name__ == '__main__':
    main()
