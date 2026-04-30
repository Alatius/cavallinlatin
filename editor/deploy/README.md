# Deploy runbook

Target: `/var/www/cavallinlatin/editor/` on the Apache server hosting alatius.com.

## One-time

```bash
# On the server
sudo mkdir -p /var/www
cd /var/www
sudo chown $USER:$USER .
git clone <this-repo-url> cavallinlatin
cd cavallinlatin/editor

# Backend venv
python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -e .

# Configure
cp .env.example .env
# Edit .env:
#   CAVALLIN_COOKIE_SECURE=true
#   CAVALLIN_BASE_PATH=/cavallinlatin

# Regenerate column PNGs from the committed TIFFs (takes ~2-3 min, produces
# ~170 MB under editor/data/columns/ — gitignored, so must be rebuilt here).
backend/.venv/bin/python -m app.scripts.convert_tiff_to_png

# Populate the DB and seed admin. Run from backend/ so `python -m` finds the app package.
cd backend
../backend/.venv/bin/python -m app.scripts.import_xml
../backend/.venv/bin/python -m app.scripts.create_admin
cd ..

# Permissions
sudo chown -R www-data:www-data /var/www/cavallinlatin
sudo chmod 640 /var/www/cavallinlatin/editor/.env

# systemd
sudo cp deploy/cavallinlatin.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cavallinlatin.service

# Apache
sudo a2enmod proxy proxy_http expires headers
# Paste the contents of deploy/apache-vhost.conf into the alatius.com
# <VirtualHost> block in /etc/apache2/sites-available/alatius.conf
sudo apachectl configtest && sudo systemctl reload apache2

# Build and deploy the frontend (repeat on every frontend change)
cd /var/www/cavallinlatin/editor/frontend
npm ci
npm run build
# dist/ is served directly by Apache via the Alias in apache-vhost.conf
```

## Nightly backup (cron)

```cron
0 3 * * * www-data cd /var/www/cavallinlatin/editor/backend && \
    /var/www/cavallinlatin/editor/backend/.venv/bin/python -m app.scripts.backup_db
```

`backup_db.py` self-prunes to the 30 most recent snapshots. For off-box safety,
add an `rsync` of `editor/data/backups/` to a separate host.

## Updating

1. `git pull` on the server.
2. If TIFFs changed: rerun `python -m app.scripts.convert_tiff_to_png` (it skips files that already exist — pass `--force` to re-do everything).
3. If Python deps changed: `backend/.venv/bin/pip install -e .`
4. If the frontend changed: `cd frontend && npm ci && npm run build`.
5. `sudo systemctl restart cavallinlatin.service`.

## Releasing edits back to the master XML

Edits live in SQLite (`editor/data/cavallin.db`). To produce a new master
`cavallinlatin.xml` and commit it to git — done manually, roughly once a year
when cutting a release:

```bash
ssh into the server
cd /var/www/cavallinlatin/editor/backend
../backend/.venv/bin/python -m app.scripts.export_xml
cd /var/www/cavallinlatin
git diff editor/data/cavallinlatin.xml    # sanity-check the delta
git add editor/data/cavallinlatin.xml
git commit -m "Release YYYY-MM: export edits from editor"
git push
```

## Smoke test

After deploy, visit:

- `https://alatius.com/cavallinlatin/` — home page with lookup box.
- `https://alatius.com/cavallinlatin/entry/abacus` — single entry + column image.
- `https://alatius.com/cavallinlatin/search?q=amor` — search results.
- `https://alatius.com/cavallinlatin/editor/login` — login.

`curl https://alatius.com/cavallinlatin/api/entries/abacus` should return JSON.
