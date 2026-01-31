# Deploy FastAPI to Google Cloud Run

This guide is written as a **step-by-step checklist** that an automated agent (or human) can follow to deploy a FastAPI application to **Google Cloud Run**.

---

## Prerequisites

* A working **FastAPI** application
* **Python 3.10+**
* **Docker** installed locally
* A **Google Cloud account**
* A **Google Cloud project**
* `gcloud` CLI installed

---

## 1. Project Structure

Ensure your project looks like this:

```
project-root/
├── main.py
├── requirements.txt
└── Dockerfile
```

---

## 2. FastAPI Application

Create or verify `main.py`:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello from Cloud Run"}
```

Test locally:

```bash
uvicorn main:app --reload
```

---

## 3. Dependencies

Create `requirements.txt`:

```txt
fastapi
uvicorn[standard]
```

Add any additional dependencies your app requires.

---

## 4. Dockerfile (Required)

Create a file named `Dockerfile` (no extension):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

> ⚠️ Cloud Run **requires port 8080**.

---

## 5. Install & Verify Google Cloud CLI

Install the Google Cloud SDK if needed:

[https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)

Verify installation:

```bash
gcloud --version
```

---

## 6. Authenticate & Set Project

Login:

```bash
gcloud auth login
```

Set your project:

```bash
gcloud config set project YOUR_PROJECT_ID
```

(Optional) Create a new project:

```bash
gcloud projects create my-fastapi-project
gcloud config set project my-fastapi-project
```

---

## 7. Enable Required Google Cloud Services (One-Time)

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

---

## 8. Deploy to Cloud Run

Run this command from the project root:

```bash
gcloud run deploy fastapi-app \
  --source . \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated
```

Deployment steps handled automatically:

* Build container image
* Push to Artifact Registry
* Deploy to Cloud Run
* Generate public HTTPS URL

---

## 9. Access the Live Service

After deployment, note the service URL:

```
https://fastapi-app-xxxxx-ew.a.run.app
```

Test:

```bash
curl https://fastapi-app-xxxxx-ew.a.run.app
```

---

## 10. Environment Variables (Optional)

Set environment variables:

```bash
gcloud run services update fastapi-app \
  --set-env-vars ENV=production,DATABASE_URL=postgres://...
```

Access in code:

```python
import os
os.getenv("DATABASE_URL")
```

---

## 11. Authentication (Optional)

Make the service private:

```bash
gcloud run services update fastapi-app --no-allow-unauthenticated
```

Use IAM, Firebase Auth, or IAP for access control.

---

## 12. Performance & Scaling Options (Optional)

Increase resources:

```bash
--cpu 1 --memory 512Mi --concurrency 80
```

Prevent cold starts (costs money):

```bash
--min-instances 1
```

---

## 13. Cost Expectations

For a small app (~100 daily active users):

* Covered by **Cloud Run free tier**
* Expected cost: **$0 – $5 / month**

---

## 14. Common Mistakes to Avoid

* ❌ Using port 8000 instead of 8080
* ❌ Missing `requirements.txt`
* ❌ Forgetting `--allow-unauthenticated`
* ❌ Running infinite background loops
* ❌ Setting `min-instances > 0` unknowingly

---

## 15. Deployment Checklist

* [ ] FastAPI app runs locally
* [ ] Dockerfile present
* [ ] Port set to 8080
* [ ] Google Cloud project selected
* [ ] Required APIs enabled
* [ ] Cloud Run deploy successful
* [ ] Public URL reachable

---

## ✅ Done

Your FastAPI app is now running on **Google Cloud Run** with auto-scaling, HTTPS, and near-zero cost for small usage.
