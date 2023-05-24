from .smartdash_server import main as smartdash_main
import os
import argparse
import subprocess


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true", help="Run smartdash_server")
    parser.add_argument(
        "--dash", action="store_true", help="Run dash.py with Streamlit"
    )
    parser.add_argument("--port", type=int, help="Port number for the server")
    parser.add_argument("--server_url", type=str, help="server url for use with --dash")

    args = parser.parse_args()

    if args.server_url:
        os.environ["SMARTDASH_SERVER_URL"] = str(args.server_url)

    if not args.port:
        args.port = 8080

    if args.server:
        smartdash_main(port=args.port)
    elif args.dash:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dash_file = os.path.join(current_dir, "dash.py")
        subprocess.run(
            [
                "streamlit",
                "run",
                dash_file,
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
                "--server.port",
                str(args.port),
            ]
        )
    else:
        parser.print_help()


cli()
