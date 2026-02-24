#!/usr/bin/env python3
"""
import_templates.py - Import wiki templates, forms, categories, and pages into MediaWiki.

Uses the MediaWiki Action API to create all the structured content pages.
Run this after setup_wiki.sh has completed and the wiki is running.

Usage: python3 scripts/import_templates.py [--wiki-url URL] [--user USER] [--password PASS]
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"


class WikiImporter:
    """Handles authenticated page creation via the MediaWiki API."""

    def __init__(self, api_url: str, username: str, password: str):
        self.api_url = api_url
        self.session = requests.Session()
        self.csrf_token = None
        self._login(username, password)

    def _login(self, username: str, password: str):
        """Login to MediaWiki and obtain CSRF token."""
        # Get login token
        resp = self.session.get(self.api_url, params={
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json",
        })
        resp.raise_for_status()
        login_token = resp.json()["query"]["tokens"]["logintoken"]

        # Login
        resp = self.session.post(self.api_url, data={
            "action": "login",
            "lgname": username,
            "lgpassword": password,
            "lgtoken": login_token,
            "format": "json",
        })
        resp.raise_for_status()
        result = resp.json()
        if result.get("login", {}).get("result") != "Success":
            print(f"ERROR: Login failed: {result}")
            sys.exit(1)
        print(f"Logged in as {username}")

        # Get CSRF token
        resp = self.session.get(self.api_url, params={
            "action": "query",
            "meta": "tokens",
            "format": "json",
        })
        resp.raise_for_status()
        self.csrf_token = resp.json()["query"]["tokens"]["csrftoken"]

    def create_page(self, title: str, content: str, summary: str = "Auto-import") -> bool:
        """Create or overwrite a wiki page."""
        resp = self.session.post(self.api_url, data={
            "action": "edit",
            "title": title,
            "text": content,
            "token": self.csrf_token,
            "format": "json",
            "summary": summary,
            "bot": True,
        })
        resp.raise_for_status()
        result = resp.json()

        if "error" in result:
            print(f"  ERROR creating '{title}': {result['error']}")
            return False

        edit_result = result.get("edit", {}).get("result", "Unknown")
        if edit_result == "Success":
            return True
        else:
            print(f"  WARNING: '{title}' result: {edit_result}")
            return False

    def page_exists(self, title: str) -> bool:
        """Check if a page already exists."""
        resp = self.session.get(self.api_url, params={
            "action": "query",
            "titles": title,
            "format": "json",
        })
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        return all(int(pid) > 0 for pid in pages.keys())


def import_templates(wiki: WikiImporter):
    """Import all template wiki files."""
    template_dir = DATA_DIR / "templates"
    templates = {
        "Template:Property": "Property.wiki",
        "Template:Person": "Person.wiki",
        "Template:Era": "Era.wiki",
        "Template:Source": "Source.wiki",
        "Template:SanbornSheet": "SanbornSheet.wiki",
        "Template:CensusRecord": "CensusRecord.wiki",
    }

    print("\n=== Importing Templates ===")
    for title, filename in templates.items():
        filepath = template_dir / filename
        if not filepath.exists():
            print(f"  SKIP: {filename} not found")
            continue
        content = filepath.read_text()
        ok = wiki.create_page(title, content, "Import template")
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {title}")


def import_forms(wiki: WikiImporter):
    """Import all Page Forms definitions."""
    forms_dir = DATA_DIR / "forms"
    forms = {
        "Form:Property": "PropertyForm.wiki",
        "Form:Person": "PersonForm.wiki",
        "Form:CensusEntry": "CensusEntryForm.wiki",
    }

    print("\n=== Importing Forms ===")
    for title, filename in forms.items():
        filepath = forms_dir / filename
        if not filepath.exists():
            print(f"  SKIP: {filename} not found")
            continue
        content = filepath.read_text()
        ok = wiki.create_page(title, content, "Import form")
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {title}")


def import_categories(wiki: WikiImporter):
    """Import all category pages from categories.json."""
    categories_file = DATA_DIR / "categories.json"
    if not categories_file.exists():
        print("\n  SKIP: categories.json not found")
        return

    with open(categories_file) as f:
        data = json.load(f)

    categories = data.get("categories", [])
    print(f"\n=== Importing Categories ({len(categories)} pages) ===")

    ok_count = 0
    fail_count = 0
    for cat in categories:
        title = cat["title"]
        content = cat["content"]
        ok = wiki.create_page(title, content, "Import category")
        if ok:
            ok_count += 1
        else:
            fail_count += 1
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {title}")

    print(f"  Categories: {ok_count} OK, {fail_count} failed")


def import_pages(wiki: WikiImporter):
    """Import documentation and content pages."""
    pages_dir = DATA_DIR / "pages"
    if not pages_dir.exists():
        print("\n  SKIP: pages directory not found")
        return

    print("\n=== Importing Content Pages ===")
    ok_count = 0

    for wiki_file in sorted(pages_dir.glob("*.wiki")):
        # Derive page title from filename
        # Convention: Underscores become spaces, colons stay
        # e.g., "Project_About.wiki" -> "Project:About"
        # e.g., "Main_Page.wiki" -> "Main Page"
        title = wiki_file.stem.replace("_", " ")
        # Handle namespace prefixes encoded with double underscore
        title = title.replace("Project ", "Project:", 1) if title.startswith("Project ") else title

        content = wiki_file.read_text()
        ok = wiki.create_page(title, content, "Import content page")
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {title}")
        if ok:
            ok_count += 1

    print(f"  Pages imported: {ok_count}")


def import_eras(wiki: WikiImporter):
    """Import era pages."""
    eras_file = DATA_DIR / "seed" / "eras.json"
    if not eras_file.exists():
        print("\n  SKIP: eras.json not found")
        return

    with open(eras_file) as f:
        data = json.load(f)

    eras = data.get("eras", [])
    print(f"\n=== Importing Era Pages ({len(eras)} pages) ===")

    for era in eras:
        title = era["title"]
        content = era["content"]
        ok = wiki.create_page(title, content, "Import era page")
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {title}")


def main():
    parser = argparse.ArgumentParser(description="Import wiki templates and content")
    parser.add_argument("--wiki-url", default=None, help="MediaWiki API URL")
    parser.add_argument("--user", default=None, help="Wiki admin username")
    parser.add_argument("--password", default=None, help="Wiki admin password")
    args = parser.parse_args()

    # Load from .env if not provided
    env_path = PROJECT_DIR / ".env"
    env_vars = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip()

    api_url = args.wiki_url or env_vars.get("WIKI_SERVER", "http://localhost:8080") + "/api.php"
    username = args.user or env_vars.get("WIKI_ADMIN_USER", "Admin")
    password = args.password or env_vars.get("WIKI_ADMIN_PASSWORD", "")

    if not password:
        print("ERROR: No password provided. Set WIKI_ADMIN_PASSWORD in .env or use --password")
        sys.exit(1)

    print(f"Wiki API: {api_url}")

    wiki = WikiImporter(api_url, username, password)

    import_templates(wiki)
    import_forms(wiki)
    import_categories(wiki)
    import_eras(wiki)
    import_pages(wiki)

    print("\n=== Import Complete ===")


if __name__ == "__main__":
    main()
