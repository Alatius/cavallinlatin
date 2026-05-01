# Deploy runbook

Target: `/var/www/cavallinlatin/editor/` on the Apache server hosting alatius.com.

## One-time

```bash
# On the server.
sudo apt install -y python3.12-venv npm
sudo git clone https://github.com/Alatius/cavallinlatin.git /var/www/cavallinlatin
cd /var/www/cavallinlatin/editor

# Backend venv
sudo python3.12 -m venv backend/.venv
sudo backend/.venv/bin/pip install -e .

# Configure
sudo cp .env.example .env
# Edit .env:
#   CAVALLIN_COOKIE_SECURE=true
#   CAVALLIN_BASE_PATH=/cavallinlatin

# Regenerate column PNGs from the committed TIFFs (~10–15 min on a small VPS,
# produces ~170 MB under editor/data/columns/ — gitignored, so must be rebuilt
# here).
sudo backend/.venv/bin/python -m app.scripts.convert_tiff_to_png

# Populate the DB and seed admin. Run from backend/ so `python -m` finds the app package.
cd backend
sudo ../backend/.venv/bin/python -m app.scripts.import_xml
sudo ../backend/.venv/bin/python -m app.scripts.create_admin
cd ..

# Permissions
sudo chown -R www-data:www-data /var/www/cavallinlatin
sudo chmod 640 /var/www/cavallinlatin/editor/.env

# systemd
sudo cp deploy/cavallinlatin.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cavallinlatin.service

# Apache. Modules: a2enmod proxy proxy_http expires headers
# Add this single line inside the existing alatius.com SSL <VirtualHost> block
# in /etc/apache2/sites-available/default-ssl.conf, just before </VirtualHost>:
#
#     Include /var/www/cavallinlatin/editor/deploy/apache-vhost.conf
#
# (Using Include rather than pasting the snippet lets future changes to
# apache-vhost.conf land via `git pull` + `systemctl reload apache2`, with no
# edits to apache config files.)
sudo apachectl configtest && sudo systemctl reload apache2

# Build the frontend (repeat on every frontend change). Apache serves
# editor/frontend/dist/ directly via the Alias in apache-vhost.conf.
cd /var/www/cavallinlatin/editor/frontend
sudo npm ci
sudo npm run build
```

## Weekly backup (cron, optional)

The master XML committed to git via `export_xml.py` is the real long-term
backup. The SQLite snapshot below only protects the window between two
`export_xml` releases — i.e. recent edits that haven't been exported yet.
Skip this until that window is worth protecting.

```cron
0 3 * * 0 www-data cd /var/www/cavallinlatin/editor/backend && \
    /var/www/cavallinlatin/editor/backend/.venv/bin/python -m app.scripts.backup_db
```

`backup_db.py` self-prunes to the 8 most recent snapshots (~2 months at
weekly cadence). For off-box safety, add an `rsync` of
`editor/data/backups/` to a separate host.

## Updating

Every push to `master` triggers `.github/workflows/ci.yml`. After the
backend and frontend jobs pass, the `deploy` job SSHes into the server as
the `deploy` user and runs `editor/deploy/deploy.sh`, which pulls, rebuilds
the frontend, reinstalls the backend (no-op if deps unchanged), and
restarts the service.

The `deploy` user is restricted: its `authorized_keys` forces
`deploy.sh` (so a leaked key can only trigger a deploy), and its sole
sudo right is `systemctl restart cavallinlatin.service`. Source tree is
owned by `deploy:www-data` mode `g+rX` so the running service can read it;
`editor/data/` stays `www-data:www-data` since that's the only path the
service writes to.

To deploy manually (for debugging or to bypass CI), SSH in as yourself:

```bash
ssh alatius.com
sudo -u deploy /var/www/cavallinlatin/editor/deploy/deploy.sh
```

If TIFFs ever need re-converting (they shouldn't, since they're frozen),
that's still a one-off:

```bash
sudo -u www-data /var/www/cavallinlatin/editor/backend/.venv/bin/python \
    -m app.scripts.convert_tiff_to_png
```

## Releasing edits back to the master XML

Edits live in SQLite (`editor/data/cavallin.db`). To produce a new master
`cavallinlatin.xml` and commit it to git — done manually, roughly once a year
when cutting a release:

```bash
ssh into the server
cd /var/www/cavallinlatin/editor/backend
sudo ../backend/.venv/bin/python -m app.scripts.export_xml
cd /var/www/cavallinlatin
sudo git diff editor/data/cavallinlatin.xml    # sanity-check the delta
sudo git add editor/data/cavallinlatin.xml
sudo git commit -m "Release YYYY-MM: export edits from editor"
sudo git push
```

## Smoke test

After deploy, visit:

- `https://alatius.com/cavallinlatin/` — home page with lookup box.
- `https://alatius.com/cavallinlatin/entry/abacus` — single entry + column image.
- `https://alatius.com/cavallinlatin/search?q=amor` — search results.
- `https://alatius.com/cavallinlatin/editor/login` — login.

`curl https://alatius.com/cavallinlatin/api/entries/abacus` should return JSON.
