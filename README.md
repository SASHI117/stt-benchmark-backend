# Benchmarking_STT_backend

FastAPI-based backend service for the **Farm Vaidya Speech-to-Text Benchmarking Platform**, integrating multiple Speech-to-Text (STT) providers to evaluate transcription accuracy (WER), latency, and performance via REST APIs.

---

## 📌 Overview

This backend is designed to benchmark multiple Speech-to-Text providers using the **same audio input**, enabling fair comparison across models.
The service exposes REST APIs that accept audio files and return transcription results along with accuracy and latency metrics.

---

## 🧱 Technology Stack

* **Language:** Python 3.10+
* **Framework:** FastAPI
* **API Architecture:** REST
* **Database:** PostgreSQL (Railway managed) with SQLite fallback
* **Deployment Platform:** Railway
* **Version Control:** GitHub (FarmVaidya Organization)

---

## 📂 Project Structure

```
Benchmarking_STT_backend/
├── metrics/
│   ├── text_normalize.py
│   └── wer.py
├── azure_stt.py
├── elevenlabs_stt.py
├── google_stt.py
├── openai_stt.py
├── revai_stt.py
├── sarvam_stt.py
├── soniox_stt.py
├── database.py
├── models.py
├── create_tables.py
├── main.py
├── requirements.txt
├── README.md
```

---

## 🚀 Deployment Flow (Exact Steps Used)

### 1️⃣ GitHub Repository

* Backend code is stored in the **FarmVaidya GitHub organization**
* Repository name:
  **`Benchmarking_STT_backend`**
* No api keys or `.env` file are committed to GitHub

---

### 2️⃣ Railway Deployment

The backend is deployed by **directly connecting Railway to the GitHub repository**.

Steps:

1. Open **Railway**
2. Click **New Project**
3. Select **Deploy from GitHub**
4. Choose:

   ```
   farmvaidya-ai / Benchmarking_STT_backend
   ```
5. Railway automatically:

   * Detects a Python project
   * Installs dependencies from `requirements.txt`
   * Starts the FastAPI app

---

### 3️⃣ Environment Variables Configuration

All secrets are added directly in **Railway → Service → Variables**.

Variables configured:

```
OPENAI_API_KEY
ELEVENLABS_API_KEY
GOOGLE_STT_API_KEY
REVAI_API_KEY
SARVAM_API_KEY
SONIOX_API_KEY
SPEECH_KEY
ENDPOINT
```

✔ No `.env` file in GitHub
✔ Secrets injected securely at runtime by Railway

---

### 4️⃣ Application Start

Railway automatically runs the backend using:

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

This happens internally — no manual configuration required.

---

### 5️⃣ Custom Domain Setup

* A **custom domain** is added via Railway
* Railway automatically:

  * Handles DNS routing
  * Enables HTTPS
  * Routes traffic to the FastAPI backend

The backend becomes publicly accessible through the custom domain.

---

## 🔗 API Endpoint

### Benchmark API

```
POST /benchmark
```

**Accepts:**

* Audio file
* Reference transcript
* Language code (optional)

**Returns:**

* STT provider name
* Model name
* Transcription output
* Word Error Rate (WER)
* Latency (ms)
* Status (success/failure)

---

## 📦 Dependencies

All required dependencies are listed in `requirements.txt`.
Railway installs them automatically during deployment.

---

## 🧠 Key Design Decisions

* Environment variables used for all secrets
* No credentials committed to GitHub
* Same codebase works locally and in production
* Railway-managed PostgreSQL used in production
* SQLite fallback available for local testing

---

## 📌 Versioning

* **v1.0** – STT Benchmarking Platform
* **v1.1 (Planned)** – AI4Bharat & Bhashini integration

---

## 📝 One-line Summary

> This backend benchmarks multiple Speech-to-Text providers using a FastAPI REST service, deployed automatically on Railway via GitHub integration with secure environment variable management.

---
