#!/usr/bin/env bash
# setup_wiki.sh - Initial setup for Benicia Historic Homes Wiki
# Run this once after cloning the repository.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Load environment variables
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.example to .env and configure it."
    exit 1
fi
set -a
source .env
set +a

echo "=== Benicia Historic Homes Wiki Setup ==="
echo ""

# Step 1: Start Docker containers
echo "[1/8] Starting Docker containers..."
docker compose up -d
echo "Waiting for MariaDB to be healthy..."
sleep 5
until docker exec benicia-db healthcheck.sh --connect --innodb_initialized 2>/dev/null; do
    echo "  ...waiting for database..."
    sleep 3
done
echo "Database is ready."

# Step 2: Run MediaWiki installer
echo ""
echo "[2/8] Running MediaWiki installation..."
# Check if LocalSettings.php already indicates a configured wiki
if docker exec benicia-wiki test -f /var/www/html/LocalSettings.php 2>/dev/null; then
    echo "  MediaWiki appears to already be installed. Checking..."
    # Try to access the API to see if it's working
    if curl -sf "http://localhost:8080/api.php?action=query&meta=siteinfo&format=json" > /dev/null 2>&1; then
        echo "  Wiki is already running. Skipping installation."
        SKIP_INSTALL=true
    else
        SKIP_INSTALL=false
    fi
else
    SKIP_INSTALL=false
fi

if [ "${SKIP_INSTALL:-false}" = "false" ]; then
    # Remove any existing LocalSettings.php inside container so installer will run
    docker exec benicia-wiki rm -f /var/www/html/LocalSettings.php 2>/dev/null || true

    docker exec benicia-wiki php maintenance/run.php install.php \
        --dbserver=db \
        --dbname="${DB_NAME}" \
        --dbuser="${DB_USER}" \
        --dbpass="${DB_PASSWORD}" \
        --server="${WIKI_SERVER}" \
        --scriptpath="" \
        --lang=en \
        --pass="${WIKI_ADMIN_PASSWORD}" \
        "${WIKI_NAME}" \
        "${WIKI_ADMIN_USER}"

    echo "  MediaWiki installed successfully."

    # Copy the generated LocalSettings.php out of the container for reference
    docker cp benicia-wiki:/var/www/html/LocalSettings.php "$PROJECT_DIR/LocalSettings.generated.php"
    echo "  Generated LocalSettings.php saved to LocalSettings.generated.php"
fi

# Step 3: Copy our custom LocalSettings.php into the container
echo ""
echo "[3/8] Applying custom LocalSettings.php..."
docker cp "$PROJECT_DIR/LocalSettings.php" benicia-wiki:/var/www/html/LocalSettings.php
docker exec benicia-wiki chown www-data:www-data /var/www/html/LocalSettings.php

# Step 4: Install Composer dependencies (Semantic MediaWiki, Page Forms)
echo ""
echo "[4/8] Installing Semantic MediaWiki via Composer..."
docker exec benicia-wiki bash -c '
    cd /var/www/html
    # Install composer if not present
    if [ ! -f composer.phar ]; then
        curl -sS https://getcomposer.org/installer | php
    fi
    # Update composer.local.json for SMW and PageForms
    cat > composer.local.json << "COMPOSER_EOF"
{
    "require": {
        "mediawiki/semantic-media-wiki": "~4.1",
        "mediawiki/page-forms": "~5.8",
        "mediawiki/semantic-result-formats": "~4.2",
        "mediawiki/maps": "~10.2"
    }
}
COMPOSER_EOF
    php composer.phar update --no-dev 2>&1
'
echo "  Extensions installed via Composer."

# Step 5: Run database update for extensions
echo ""
echo "[5/8] Running database update (extension tables)..."
docker exec benicia-wiki php maintenance/run.php update.php --quick
echo "  Database updated."

# Step 6: Set up Semantic MediaWiki tables
echo ""
echo "[6/8] Setting up Semantic MediaWiki data store..."
docker exec benicia-wiki php extensions/SemanticMediaWiki/maintenance/setupStore.php
echo "  SMW data store initialized."

# Step 7: Verify installation
echo ""
echo "[7/8] Verifying installation..."
# Check that the wiki API responds
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/api.php?action=query&meta=siteinfo&format=json")
if [ "$HTTP_CODE" = "200" ]; then
    echo "  Wiki API is responding (HTTP $HTTP_CODE)."
else
    echo "  WARNING: Wiki API returned HTTP $HTTP_CODE. Check logs with: docker logs benicia-wiki"
fi

# Step 8: Print summary
echo ""
echo "[8/8] Setup complete!"
echo ""
echo "=== Summary ==="
echo "Wiki URL:       ${WIKI_SERVER}"
echo "Admin user:     ${WIKI_ADMIN_USER}"
echo "Admin password:  (see .env file)"
echo ""
echo "=== Next Steps ==="
echo "1. Visit ${WIKI_SERVER} to verify the wiki is running"
echo "2. Run: python3 scripts/download_gis_data.py    (download GIS data)"
echo "3. Run: python3 scripts/import_templates.py      (import templates and forms)"
echo "4. Run: python3 scripts/create_stubs.py          (create property stub pages)"
echo "5. Run: python3 scripts/index_sanborn.py         (create Sanborn map index)"
echo ""
