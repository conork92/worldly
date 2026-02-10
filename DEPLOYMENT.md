# Deployment Guide

This guide covers deploying the Worldly application using Docker to various Platform-as-a-Service (PaaS) providers.

## Prerequisites

- Docker installed locally (for testing)
- Git repository set up
- Supabase credentials (SUPABASE_URL, SUPABASE_ANON_KEY)
- API_KEY for write operations

## Local Development with Docker

### Using Docker Compose (Recommended)

1. Create a `.env` file in the `app/` directory:
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
API_KEY=your_api_key
```

2. Build and run:
```bash
docker-compose up --build
```

3. Access the application at `http://localhost:8000`

### Using Docker directly

1. Build the image:
```bash
docker build -t worldly-app .
```

2. Run the container:
```bash
docker run -d \
  -p 8000:8000 \
  -e SUPABASE_URL=your_supabase_url \
  -e SUPABASE_ANON_KEY=your_supabase_anon_key \
  -e API_KEY=your_api_key \
  --name worldly-app \
  worldly-app
```

## Deploying to PaaS Providers

### Google Cloud Run (deploy on push to main)

Deploys automatically when you push to the `main` branch. The workflow (`.github/workflows/deploy-cloudrun.yml`) builds from the repo Dockerfile and deploys to Cloud Run.

**Steps at a glance**

1. Create a GCP project and enable Cloud Run, Cloud Build, and Artifact Registry APIs.
2. Create a service account with Cloud Run Admin + Service Account User + Storage Admin; download its JSON key.
3. In GitHub: Settings → Secrets and variables → Actions → add `GCP_PROJECT_ID`, `GCP_SA_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `API_KEY`.
4. Push (or merge) to `main`; the workflow builds and deploys. Get the URL from the Cloud Run console or the workflow run.

---

**1. GCP setup**

- Create a [Google Cloud project](https://console.cloud.google.com/) (or use an existing one).
- Enable APIs:
  - [Cloud Run API](https://console.cloud.google.com/apis/library/run.googleapis.com)
  - [Cloud Build API](https://console.cloud.google.com/apis/library/cloudbuild.googleapis.com)
  - [Artifact Registry API](https://console.cloud.google.com/apis/library/artifactregistry.googleapis.com) (used by Cloud Build).
- Create a **service account** for GitHub Actions:
  - IAM & Admin → Service Accounts → Create.
  - Name it e.g. `github-actions-cloudrun`.
  - Grant roles: **Cloud Run Admin**, **Service Account User**, **Storage Admin** (or **Artifact Registry Writer**).
  - Create a **JSON key**: Keys → Add key → JSON, download the file.

**2. GitHub secrets**

In your repo: **Settings → Secrets and variables → Actions**. Add:

| Secret        | Description |
|---------------|-------------|
| `GCP_PROJECT_ID` | Your GCP project ID (e.g. `my-project-123`) |
| `GCP_SA_KEY`     | Full contents of the service account JSON key file |
| `SUPABASE_URL`   | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `API_KEY`       | API key for app write operations |

**Optional – same env as CLI:** To give the container the exact same env as when you deploy with `--env-vars-file .env`, add a secret **`CLOUD_RUN_ENV`** and paste your full `.env` contents (one `KEY=VALUE` per line). The workflow will use it as the env file for the service. If `CLOUD_RUN_ENV` is not set, it falls back to the three vars above.

**3. Optional: repo variables**

Under **Settings → Secrets and variables → Actions → Variables** you can set:

- `GCP_REGION` – e.g. `europe-west1` (default if unset).
- `CLOUD_RUN_SERVICE` – Cloud Run service name (default: `worldly`).

**4. Deploy**

Push to `main`. The workflow will build the image with Cloud Build and deploy to Cloud Run. The first run may take a few minutes. The service URL will appear in the workflow summary and in the Cloud Run console.

**Initial deploy from CLI**

Do the first deploy from your machine so the service (and any GCP resources) exist; after that, pushes to `main` will update it.

1. **Install and log in** (if needed):
   ```bash
   # Install: https://cloud.google.com/sdk/docs/install
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Enable required APIs**:
   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
   ```

3. **Deploy from the repo root** (where the Dockerfile is):
   ```bash
   cd /path/to/worldly
   gcloud run deploy worldly \
     --source . \
     --region europe-west1 \
     --platform managed \
     --allow-unauthenticated \
     --set-env-vars "SUPABASE_URL=your_supabase_url,SUPABASE_ANON_KEY=your_anon_key,API_KEY=your_api_key"
   ```
   Replace `your_supabase_url`, `your_anon_key`, and `your_api_key` with your real values (no spaces after commas).

   **Or** use your `.env` file directly (gcloud accepts `KEY=VALUE` per line):
   ```bash
   gcloud run deploy worldly \
     --source . \
     --region europe-west1 \
     --platform managed \
     --allow-unauthenticated \
     --env-vars-file .env
   ```
   If you get errors (e.g. from `#` comment lines), remove those lines from `.env` or run `python3 env_to_yaml.py` and use `--env-vars-file env.cloudrun.yaml` instead.

4. When the deploy finishes, the CLI prints the service URL. Open it in a browser to confirm the app is running.

---

### Railway

1. Connect your GitHub repository to Railway
2. Add environment variables in Railway dashboard:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `API_KEY`
3. Railway will automatically detect the Dockerfile and deploy

### Render

1. Create a new Web Service
2. Connect your GitHub repository
3. Set build command: `docker build -t worldly-app .`
4. Set start command: `docker run -p $PORT:8000 worldly-app`
5. Add environment variables in the dashboard

### Fly.io

1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Launch: `fly launch`
4. Set secrets:
```bash
fly secrets set SUPABASE_URL=your_supabase_url
fly secrets set SUPABASE_ANON_KEY=your_supabase_anon_key
fly secrets set API_KEY=your_api_key
```

### Heroku

1. Install Heroku CLI
2. Login: `heroku login`
3. Create app: `heroku create your-app-name`
4. Set config vars:
```bash
heroku config:set SUPABASE_URL=your_supabase_url
heroku config:set SUPABASE_ANON_KEY=your_supabase_anon_key
heroku config:set API_KEY=your_api_key
```
5. Deploy: `git push heroku main`

Note: Heroku requires a `Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### DigitalOcean App Platform

1. Connect GitHub repository
2. Select Dockerfile as build method
3. Add environment variables in the dashboard
4. Deploy

## Environment Variables

Required environment variables:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anonymous key
- `API_KEY`: API key for write operations (optional but recommended)

## GitHub Actions CI/CD (Optional)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Railway
        uses: bervProject/railway-deploy@v0.2.1
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: your-service-name
```

## Health Checks

The application includes a health check endpoint. Most PaaS providers will automatically use this to monitor the application.

## Troubleshooting

1. **Port binding**: Ensure the PaaS provider uses port 8000 or configure the PORT environment variable
2. **Environment variables**: Verify all required variables are set
3. **Build errors**: Check Docker logs for dependency issues
4. **Database connection**: Verify Supabase credentials are correct

## Production Considerations

1. Remove volume mounts from docker-compose.yml for production
2. Use environment variables instead of .env files
3. Enable HTTPS/SSL
4. Set up proper logging and monitoring
5. Configure CORS appropriately for your domain
6. Use a reverse proxy (nginx) if needed
