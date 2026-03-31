#!main.py
import argparse
import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)

def main() -> None:
    """
    Root entry point for the Autonomous Engineering platform.
    Provides CLI commands to start the API, Worker, or the full Docker stack.
    """
    parser = argparse.ArgumentParser(description="Autonomous Engineer CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command to start the API server locally
    subparsers.add_parser("start-api", help="Start the FastAPI server locally")
    
    # Command to start the Celery worker locally
    subparsers.add_parser("start-worker", help="Start the Celery worker locally")
    
    # Command to spin up the entire Docker stack
    subparsers.add_parser("up", help="Start all services via Docker Compose")

    args = parser.parse_args()

    # Load environment variables (assumes python-dotenv is installed)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.warning("python-dotenv not installed. Skipping .env file load.")

    if args.command == "start-api":
        logger.info("Starting FastAPI server...")
        subprocess.run(["uvicorn", "autonomous_engineer.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])
        
    elif args.command == "start-worker":
        logger.info("Starting Celery worker...")
        subprocess.run(["celery", "-A", "autonomous_engineer.infra.queue", "worker", "--loglevel=info"])
        
    elif args.command == "up":
        logger.info("Spinning up the production stack via Docker Compose...")
        subprocess.run(["docker-compose", "up", "--build", "-d"])
        
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()