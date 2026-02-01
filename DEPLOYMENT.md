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
