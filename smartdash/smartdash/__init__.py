from .smartdash_server import main as smartdash_main

import argparse
import subprocess

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', action='store_true', help='Run smartdash_server')
    parser.add_argument('--dash', action='store_true', help='Run dash.py with Streamlit')
    parser.add_argument('--port', type=int, help='Port number for the server')

    args = parser.parse_args()

    if args.server:
        smartdash_main(port=args.port)
    elif args.dash:
        subprocess.run(['streamlit', 'run', 'dash.py', '--server.headless', 'true', '--browser.gatherUsageStats', 'false', '--server.port', str(args.port)])
    else:
        parser.print_help()
