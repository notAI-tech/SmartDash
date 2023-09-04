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
    parser.add_argument("--version", action="store_true", help="Print version number")
    parser.add_argument(
        "--save_dir", type=str, help="save directory for smartdash server"
    )
    parser.add_argument(
        "--base_url_path",
        type=str,
        help="base url path for use with --dash, e.g. /smartdash",
    )

    args = parser.parse_args()

    if not args.port:
        args.port = 8080

    save_dir = os.path.abspath(args.save_dir if args.save_dir else "./")
    os.makedirs(save_dir, exist_ok=True)

    if args.server:
        from .smartdash_server import main as smartdash_main

        os.environ["SMARTDASH_SAVE_DIR"] = save_dir
        smartdash_main(port=args.port)
    elif args.dash:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dash_file = os.path.join(current_dir, "dash.py")

        os.system(
            " ".join(
                [
                    f"SMARTDASH_SERVER_URL={args.server_url}",
                    f"SAVE_DIR={save_dir}",
                    "streamlit",
                    "run",
                    dash_file,
                    "--server.headless",
                    "true",
                    "--browser.gatherUsageStats",
                    "false",
                    "--server.port",
                    str(args.port),
                    f"--server.baseUrlPath {args.base_url_path}"
                    if args.base_url_path
                    else "",
                ]
            )
        )
    else:
        parser.print_help()
