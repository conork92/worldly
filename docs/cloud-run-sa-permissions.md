# Grant GitHub Actions SA permission to deploy Cloud Run (worldly)

Run these in the **same project** you use for `GCP_PROJECT_ID` in GitHub (the project where the Cloud Run service `worldly` lives).

## 1. GitHub Actions service account (caller)

```bash
export PROJECT_ID=boxd-408821   # must match GitHub secret GCP_PROJECT_ID
export SA_EMAIL=github-actions-worldly@${PROJECT_ID}.iam.gserviceaccount.com

# Required: use project APIs (Cloud Build, etc.) – fixes "Caller does not have required permission to use project"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/serviceusage.serviceUsageConsumer"

# Cloud Run: deploy, get, update, delete services
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

# Act as the runtime service account when deploying
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

# Build and push images (--source . uses Cloud Build → Artifact Registry)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer"

# Cloud Build: create and run builds (required for gcloud run deploy --source .)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudbuild.builds.editor"

# Storage: Cloud Build uses a bucket for build logs/artifacts
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.admin"
```

## 2. Default Cloud Build service account (used when building with --source .)

When you deploy with `--source .`, Cloud Build runs under a **default** service account. That account must be allowed to push images and deploy to Cloud Run. Run this once per project:

```bash
# Get project number (different from project ID)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export CLOUDBUILD_SA=${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com

# Allow the default Cloud Build SA to push images and deploy to Cloud Run
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/artifactregistry.writer"

# Optional but recommended: allow logging and storage for builds
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/storage.admin"
```

Ref: [Cloud Build service account](https://cloud.google.com/build/docs/cloud-build-service-account), [Cloud Run build service account](https://cloud.google.com/run/docs/configuring/services/build-service-account).

---

If the GitHub Actions SA was created in a **different** project, use that project's ID in `SA_EMAIL` only, but run all bindings with `PROJECT_ID` set to the project where you deploy.

After running, wait 1–2 minutes for IAM to propagate, then re-run the GitHub Action.
