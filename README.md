# AI-Powered Company Enrichment Platform

An intelligent, production-ready Company Enrichment Platform built for sales teams and business analysts. This system takes a company website URL, scrapes the target site, extracts verified contact information via regex (emails, phone numbers, office address), and infers high-value business insights (core services, target customers, customer pain points, personalized cold outreach openers) using Google Gemini AI without inventing/hallucinating contact data.

## Features

- **Asynchronous Intelligent Scraping**: Scrapes sitemaps, crawls homepage internal links, and falls back to guessed relevant paths (`/about`, `/contact`, etc.) concurrently.
- **Strict Anti-Hallucination Contact Extraction**: Extracts emails, phone numbers, and addresses strictly using Python regex patterns. The LLM is never given authorization to invent contact details.
- **Token Optimization**: Cleans HTML by stripping out headers, navbars, footers, scripts, styles, SVGs, and cookie banners before packing context.
- **Double-Layered Caching**: Checks the SQLite database for existing domains to return cached results instantly.
- **Flexible AI Inference**: Seamless integration with Google Gemini Pro API (primary) and OpenAI (fallback), with robust local heuristics if API keys are missing.
- **Premium User Interface**: Modern glassmorphic dark-mode interface built with React + Vite and Vanilla CSS. Displays insights in a detailed dashboard with toggleable responsive Table and Card Grid views.
- **Google Colab Support**: Standalone interactive script ready to be executed in Google Colab cells.

---

## Directory Structure

```text
/
├── backend/
│   ├── main.py            # FastAPI endpoints, CORS, orchestrator
│   ├── database.py        # SQLite SQLAlchemy engine & session
│   ├── models.py          # SQLAlchemy SQLite models
│   ├── schemas.py         # Pydantic schemas for verification
│   ├── scraper.py         # Async scraper and regex extractor
│   └── ai_service.py      # Gemini/OpenAI interface & fallbacks
├── frontend/
│   ├── src/
│   │   ├── main.jsx       # React mounting
│   │   ├── App.jsx        # Premium dashboard application
│   │   └── App.css        # Premium custom CSS styling
│   ├── index.html         # Document index with SEO tags
│   ├── package.json       # Frontend project manifests
│   └── vite.config.js     # Vite compilation settings
├── colab/
│   └── company_enrichment_colab.py # Standalone notebook runner script
├── requirements.txt       # Python backend dependencies
├── Dockerfile             # Multi-stage production container build
├── docker-compose.yml     # Multi-service local coordinator
├── .env.example           # Server configuration template
└── README.md              # Project documentation (this file)
```

---

## Local Setup & Run

### Method 1: Using Docker Compose (Recommended)

1. Make sure Docker and Docker Compose are installed.
2. Copy `.env.example` to `.env` and fill in your `GEMINI_API_KEY`:
   ```bash
   cp .env.example .env
   ```
3. Boot the environment:
   ```bash
   docker-compose up --build
   ```
4. Access:
   - Frontend Dashboard: [http://localhost:5173](http://localhost:5173)
   - Backend APIs Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Method 2: Manual Installation

#### Backend
1. Navigate to the root directory and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set your environment variables (on Linux/macOS `export`, on Windows PowerShell `$env:`):
   ```bash
   $env:GEMINI_API_KEY="your_api_key_here"
   ```
3. Start the FastAPI server using Uvicorn:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

#### Frontend
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Run in development mode:
   ```bash
   npm run dev
   ```
4. Access the dashboard at [http://localhost:5173](http://localhost:5173).

---

## Google Colab Notebook Implementation

To run in Google Colab:
1. Create a new notebook on Google Colab.
2. Copy the contents of the python script located at: `colab/company_enrichment_colab.py`.
3. Paste the code into a code cell and execute.
4. Input your `GEMINI_API_KEY` and the array of URLs (e.g. `['stripe.com', 'https://vercel.com']`) when prompted.
5. The notebook will print a verified, valid JSON array of company insights.

---

## API Endpoints

### 1. Enrich Company URL
- **Endpoint**: `POST /enrich`
- **Request Body**:
  ```json
  {
    "url": "https://stripe.com"
  }
  ```
- **Example Response (`200 OK`)**:
  ```json
  {
    "website_name": "Stripe",
    "company_name": "Stripe, Inc.",
    "address": "354 Oyster Point Blvd, South San Francisco, CA 94080",
    "mobile_number": "+1-888-963-8747",
    "mail": [
      "info@stripe.com",
      "support@stripe.com"
    ],
    "core_service": "Financial infrastructure platform for the internet, enabling payments processing, billing, invoicing, and corporate card issuance.",
    "target_customer": "E-commerce companies, SaaS platforms, online marketplaces, startups, and enterprises of all sizes.",
    "probable_pain_point": "Complex international payments compliance, high checkout drop-offs, payment fraud, and billing management overhead.",
    "outreach_opener": "Hi team, I noticed Stripe's payments platform supports seamless marketplace payouts. I'd love to show you how our system optimizes your checkout flows to increase conversions."
  }
  ```

### 2. Get All Results
- **Endpoint**: `GET /results`
- **Example Response (`200 OK`)**:
  ```json
  [
    {
      "id": 1,
      "website_url": "https://stripe.com",
      "website_name": "Stripe",
      "company_name": "Stripe, Inc.",
      "address": "354 Oyster Point Blvd, South San Francisco, CA 94080",
      "mobile_number": "+1-888-963-8747",
      "mail": [
        "info@stripe.com",
        "support@stripe.com"
      ],
      "core_service": "Financial infrastructure platform...",
      "target_customer": "E-commerce companies...",
      "probable_pain_point": "Complex payments...",
      "outreach_opener": "Hi team...",
      "created_at": "2026-05-30T13:10:00"
    }
  ]
  ```

---

## Production Deployment Steps

### Backend Deployment (Render)

1. Create a GitHub repository and push this codebase.
2. Sign in to **Render** ([https://render.com](https://render.com)) and click **New** -> **Web Service**.
3. Link your GitHub repository.
4. Configure the Web Service settings:
   - **Environment**: `Python` or `Docker` (Render supports building from Dockerfile directly!).
   - If using **Docker**:
     - Render will automatically look for the root `Dockerfile` and build it.
   - If using **Python** (Manual setup):
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. In the **Environment** tab, add your environment variables:
   - `GEMINI_API_KEY`: *Your Gemini Pro API Key*
   - `DATABASE_URL`: `sqlite:///./company_enrichment.db` (For persistent database, mount a Disk or link to a PostgreSQL service in Render).
6. Click **Deploy Web Service**.

### Frontend Deployment (Vercel)

1. Sign in to **Vercel** ([https://vercel.com](https://vercel.com)) and click **Add New Project**.
2. Select your GitHub repository.
3. Configure the settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend` (Important! Select the frontend folder)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Under **Environment Variables**, add:
   - `VITE_API_URL`: *Your Render backend URL (e.g. https://your-backend.onrender.com)*
5. Click **Deploy**.
