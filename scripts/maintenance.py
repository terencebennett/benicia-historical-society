#!/usr/bin/env python3
"""
maintenance.py - Backup, export, and maintenance tasks for the Benicia wiki.

Commands:
    backup          Full database backup (mysqldump)
    export-xml      Export all wiki pages as XML
    export-smw      Export Semantic MediaWiki structured data as JSON
    restore         Restore from a database backup
    stats           Show wiki statistics

Usage:
    python3 scripts/maintenance.py backup
    python3 scripts/maintenance.py export-xml
    python3 scripts/maintenance.py export-smw
    python3 scripts/maintenance.py restore backups/benicia_wiki_2024-01-15.sql
    python3 scripts/maintenance.py stats
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
BACKUP_DIR = PROJECT_DIR / "backups"


def load_env() -> dict:
    """Load environment variables from .env file."""
    env_path = PROJECT_DIR / ".env"
    env_vars = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip()
    return env_vars


def cmd_backup(args):
    """Create a full database backup using mysqldump."""
    env = load_env()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_file = BACKUP_DIR / f"benicia_wiki_{timestamp}.sql"

    db_name = env.get("DB_NAME", "benicia_wiki")
    db_user = env.get("DB_USER", "wiki")
    db_password = env.get("DB_PASSWORD", "")

    print(f"Creating database backup...")
    print(f"  Database: {db_name}")
    print(f"  Output: {backup_file}")

    cmd = [
        "docker", "exec", "benicia-db",
        "mysqldump",
        f"--user={db_user}",
        f"--password={db_password}",
        "--single-transaction",
        "--routines",
        "--triggers",
        db_name,
    ]

    try:
        with open(backup_file, "w") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"  ERROR: mysqldump failed: {result.stderr}")
            backup_file.unlink(missing_ok=True)
            return False
    except FileNotFoundError:
        print("  ERROR: docker command not found. Is Docker installed?")
        return False

    size = backup_file.stat().st_size
    print(f"  Backup complete: {size:,} bytes")

    # Compress
    try:
        subprocess.run(["gzip", str(backup_file)], check=True)
        gz_file = Path(str(backup_file) + ".gz")
        gz_size = gz_file.stat().st_size
        print(f"  Compressed: {gz_size:,} bytes ({gz_file.name})")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("  Note: gzip not available, backup saved uncompressed.")

    return True


def cmd_export_xml(args):
    """Export all wiki pages as MediaWiki XML."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    export_file = BACKUP_DIR / f"benicia_wiki_pages_{timestamp}.xml"

    print("Exporting all wiki pages as XML...")
    cmd = [
        "docker", "exec", "benicia-wiki",
        "php", "maintenance/run.php", "dumpBackup.php",
        "--full", "--quiet",
    ]

    try:
        with open(export_file, "w") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"  ERROR: Export failed: {result.stderr}")
            export_file.unlink(missing_ok=True)
            return False
    except FileNotFoundError:
        print("  ERROR: docker command not found.")
        return False

    size = export_file.stat().st_size
    print(f"  Export complete: {export_file.name} ({size:,} bytes)")
    return True


def cmd_export_smw(args):
    """Export Semantic MediaWiki data as JSON via the API."""
    env = load_env()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    api_url = env.get("WIKI_SERVER", "http://localhost:8080") + "/api.php"

    print("Exporting Semantic MediaWiki structured data...")

    # Query all properties with their SMW data
    all_data = {"properties": [], "export_date": timestamp}

    # Use SMW ask API to get all property data
    offset = 0
    batch_size = 50

    while True:
        query = (
            "[[Category:Properties]]"
            "|?Current Address|?APN|?Year Built|?Architectural Style"
            "|?Historic Status|?Stories|?Construction Material"
            "|?Current Use|?Original Use|?Data Confidence"
            "|?Latitude|?Longitude"
            f"|limit={batch_size}|offset={offset}"
        )

        resp = requests.get(api_url, params={
            "action": "ask",
            "query": query,
            "format": "json",
        }, timeout=30)

        if resp.status_code != 200:
            print(f"  WARNING: API returned {resp.status_code}")
            break

        data = resp.json()
        results = data.get("query", {}).get("results", {})

        if not results:
            break

        for page_title, page_data in results.items():
            props = page_data.get("printouts", {})
            record = {"title": page_title}
            for prop_name, prop_values in props.items():
                if prop_values:
                    # SMW returns values as lists
                    if len(prop_values) == 1:
                        val = prop_values[0]
                        if isinstance(val, dict):
                            val = val.get("fulltext", str(val))
                        record[prop_name] = val
                    else:
                        record[prop_name] = prop_values
            all_data["properties"].append(record)

        offset += batch_size
        if len(results) < batch_size:
            break

    export_file = BACKUP_DIR / f"benicia_wiki_smw_{timestamp}.json"
    with open(export_file, "w") as f:
        json.dump(all_data, f, indent=2, default=str)

    print(f"  Exported {len(all_data['properties'])} property records")
    print(f"  Output: {export_file.name}")
    return True


def cmd_restore(args):
    """Restore from a database backup."""
    env = load_env()

    backup_file = Path(args.file)
    if not backup_file.exists():
        print(f"ERROR: Backup file not found: {backup_file}")
        return False

    db_name = env.get("DB_NAME", "benicia_wiki")
    db_user = env.get("DB_USER", "wiki")
    db_password = env.get("DB_PASSWORD", "")

    print(f"Restoring database from {backup_file.name}...")
    print(f"  WARNING: This will overwrite the current database!")
    confirm = input("  Type 'yes' to confirm: ")
    if confirm.lower() != "yes":
        print("  Restore cancelled.")
        return False

    # Handle gzipped files
    if backup_file.suffix == ".gz":
        print("  Decompressing...")
        subprocess.run(["gunzip", "-k", str(backup_file)], check=True)
        backup_file = Path(str(backup_file)[:-3])  # Remove .gz

    # Copy backup into container and restore
    print("  Copying backup to container...")
    subprocess.run([
        "docker", "cp", str(backup_file), "benicia-db:/tmp/restore.sql"
    ], check=True)

    print("  Restoring database...")
    cmd = [
        "docker", "exec", "benicia-db",
        "bash", "-c",
        f"mysql --user={db_user} --password={db_password} {db_name} < /tmp/restore.sql"
    ]

    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"  ERROR: Restore failed: {result.stderr}")
        return False

    # Clean up
    subprocess.run(["docker", "exec", "benicia-db", "rm", "/tmp/restore.sql"])

    print("  Restore complete!")
    print("  Run 'docker exec benicia-wiki php maintenance/run.php update.php' to update schema.")
    return True


def cmd_stats(args):
    """Show wiki statistics."""
    env = load_env()
    api_url = env.get("WIKI_SERVER", "http://localhost:8080") + "/api.php"

    print("=== Benicia Historic Homes Wiki Statistics ===\n")

    try:
        # Get site statistics
        resp = requests.get(api_url, params={
            "action": "query",
            "meta": "siteinfo",
            "siprop": "statistics",
            "format": "json",
        }, timeout=10)
        resp.raise_for_status()
        stats = resp.json().get("query", {}).get("statistics", {})

        print(f"Total pages:    {stats.get('pages', 'N/A'):,}")
        print(f"Content pages:  {stats.get('articles', 'N/A'):,}")
        print(f"Total edits:    {stats.get('edits', 'N/A'):,}")
        print(f"Total users:    {stats.get('users', 'N/A'):,}")
        print(f"Active users:   {stats.get('activeusers', 'N/A'):,}")
        print(f"Uploaded files: {stats.get('images', 'N/A'):,}")

        # Count properties by status
        print("\n--- Properties by Status ---")
        for status in ["Stub", "Low", "Medium", "High"]:
            resp = requests.get(api_url, params={
                "action": "ask",
                "query": f"[[Category:Properties]][[Data Confidence::{status}]]|limit=0",
                "format": "json",
            }, timeout=10)
            count = resp.json().get("query", {}).get("meta", {}).get("count", "?")
            print(f"  {status}: {count}")

    except requests.RequestException as e:
        print(f"ERROR: Could not connect to wiki API: {e}")
        print("Is the wiki running? Try: docker compose up -d")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Benicia Wiki maintenance tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  backup      Create a full database backup
  export-xml  Export all wiki pages as MediaWiki XML
  export-smw  Export SMW structured data as JSON
  restore     Restore from a backup file
  stats       Show wiki statistics
""")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("backup", help="Create database backup")
    subparsers.add_parser("export-xml", help="Export pages as XML")
    subparsers.add_parser("export-smw", help="Export SMW data as JSON")

    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("file", help="Path to backup file (.sql or .sql.gz)")

    subparsers.add_parser("stats", help="Show wiki statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "backup": cmd_backup,
        "export-xml": cmd_export_xml,
        "export-smw": cmd_export_smw,
        "restore": cmd_restore,
        "stats": cmd_stats,
    }

    success = commands[args.command](args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
