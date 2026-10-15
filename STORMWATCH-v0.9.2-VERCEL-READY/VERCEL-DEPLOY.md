# STORMWATCH Vercel deployment

This ZIP has its application files at the archive root. **Extract it** and upload the contents to the root of your GitHub repository, preserving the `apps/` and `data/` folders.

Vercel settings:
- Framework Preset: Other (or auto-detected FastAPI)
- Root Directory: repository root (folder containing `pyproject.toml`)
- Leave Build Command and Output Directory unset; use the Python/FastAPI integration.
- Redeploy after committing changes.

Check `https://YOUR-DOMAIN/api/health`, then open `https://YOUR-DOMAIN/`.

The root pyproject sets the entrypoint to `apps.api.stormwatch.main:app`; the Python dependencies are also provided at the root.

Vercel limitation: WebSocket pushes and always-on background polling are disabled here. The browser checks data periodically instead. Serverless instances do not persist shared in-memory CSV uploads or caches reliably. If you need the original real-time socket updates or durable shared state, deploy the original FastAPI Docker app to an always-on host instead.

Do not upload `.env` secrets or credentials to GitHub. This is a deployment adaptation, not a verified production deployment.
