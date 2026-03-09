# 🎯 ProspectAI — Sistema de Prospección Inteligente

Sistema de prospección B2B con IA: scrapea Google Maps, puntúa leads 0-100 y los muestra en un CRM en tiempo real.

## Stack
- **Backend:** Python + Flask + PostgreSQL → Railway
- **Frontend:** HTML/JS → Vercel
- **Scraper:** Playwright (Chromium headless)

## Deploy rápido

### Backend (Railway)
1. Crear cuenta en [railway.app](https://railway.app)
2. New Project → Deploy from GitHub → seleccionar este repo
3. Add plugin → PostgreSQL
4. Las variables de entorno se configuran solas

### Frontend (Vercel)
1. Importar el repo en [vercel.com](https://vercel.com)
2. Root directory: `frontend`
3. Agregar variable: `VITE_API_URL=https://tu-backend.railway.app`

## Local dev
```bash
cd backend
pip install -r requirements.txt
playwright install chromium
python app.py
```
