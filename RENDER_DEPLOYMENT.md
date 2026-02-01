# Render Deployment Guide

## Important: Use Web Service, Not Static Site

Your application is a **FastAPI backend** that serves both API endpoints and static HTML files. You need to deploy it as a **Web Service**, not a Static Site.

## Steps to Deploy on Render

### 1. Create a New Web Service

1. Go to Render Dashboard → New → **Web Service** (NOT Static Site)
2. Connect your GitHub repository
3. Select the repository and branch (usually `main`)

### 2. Configure the Web Service

Use these settings:

**Name**: `worldly` (or your preferred name)

**Environment**: `Docker`

**Region**: Choose closest to you

**Branch**: `main` (or your default branch)

**Root Directory**: Leave empty (or use `./` if needed)

**Dockerfile Path**: `Dockerfile` (should auto-detect)

**Docker Context**: `.` (root of repository)

**Docker Command**: Leave empty (uses CMD from Dockerfile)

**Instance Type**: 
- Free tier: `Free` (for testing)
- Production: `Starter` or higher

**Auto-Deploy**: `Yes` (deploys on every push to main branch)

### 3. Environment Variables

Add these in the Render dashboard under "Environment":

```
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
API_KEY=your_api_key_here
```

**Important**: 
- Click "Add Environment Variable" for each one
- Never commit these to Git
- Use Render's environment variable section

### 4. Health Check (Optional)

Render will automatically use the HEALTHCHECK from your Dockerfile, but you can also set:

**Health Check Path**: `/api/books` (or any API endpoint)

### 5. Deploy

Click "Create Web Service" and Render will:
1. Build your Docker image
2. Start the container
3. Make it available at `https://your-app-name.onrender.com`

## Alternative: Manual Build Configuration

If you prefer not to use Docker, you can configure it manually:

**Build Command**: 
```bash
pip install -r app/requirements.txt
```

**Start Command**: 
```bash
cd app && uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Note**: Render sets the `$PORT` environment variable automatically. Your app should use this port.

## Updating Your Code for Render Port

If you're not using Docker, update `main.py` to use the PORT environment variable:

```python
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

But since you're using Docker, the Dockerfile already handles this correctly.

## Troubleshooting

1. **Build fails**: Check the build logs in Render dashboard
2. **App crashes**: Check runtime logs
3. **Environment variables not working**: Verify they're set in Render dashboard (not in code)
4. **Port issues**: Dockerfile already uses port 8000, which Render will map correctly

## Post-Deployment

After deployment:
- Your app will be at: `https://your-app-name.onrender.com`
- API endpoints: `https://your-app-name.onrender.com/api/books`
- Globe page: `https://your-app-name.onrender.com/globe`

**Note**: Free tier services on Render spin down after 15 minutes of inactivity. First request after spin-down may take 30-60 seconds.
