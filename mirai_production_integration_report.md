# MIRAI — Vercel Production Integration Report (Checkpoint 6)

**Status:** INTEGRATED & READY FOR PRODUCTION TRAFFIC  
**Date:** 2026-11-14  
**Frontend Deployment URL:** `https://mirai-jgw59fhk8-poojasrikandhula-6164s-projects.vercel.app`  
**Frontend Framework:** React 18 / TypeScript / Vite / Tailwind CSS  
**API Client:** Centralized Axios Client (`frontend/src/services/api.ts`)  
**Production Build Status:** **0 TypeScript Errors, Built Successfully (30.45s)**  

---

## 1. Vercel Production Environment Configuration

To link the deployed Vercel frontend with the cloud backend, configure the following environment variable in the Vercel Dashboard:

| Setting Key | Target Environments | Production Value | Purpose |
|:---|:---|:---|:---|
| **`VITE_API_BASE_URL`** | **Production, Preview, Development** | `https://YOUR-BACKEND-URL` *(e.g., `https://mirai-backend.onrender.com`)* | Directs all frontend network requests to the production FastAPI backend. |

### Exact Steps to Apply in Vercel Dashboard
1. Open the [Vercel Dashboard](https://vercel.com/dashboard).
2. Select the **`mirai`** project (or repository `mirai-jgw59fhk8-poojasrikandhula-6164s-projects`).
3. Navigate to **Settings** &rarr; **Environment Variables**.
4. In the **Key** field, enter:
   ```text
   VITE_API_BASE_URL
   ```
5. In the **Value** field, enter your public backend URL (without trailing slash), for example:
   ```text
   https://mirai-backend-xxxx.onrender.com
   ```
6. Check all three environments: **Production**, **Preview**, and **Development**.
7. Click **Save**.
8. Go to the **Deployments** tab, click the three dots (`...`) on the latest deployment, and select **Redeploy** (ensure "Use existing Build Cache" is unchecked so Vite picks up the new environment variable).

---

## 2. API Client Normalization & URL Handling Verification

In [frontend/src/services/api.ts](file:///c:/Users/srisa/OneDrive/Desktop/astraq/frontend/src/services/api.ts), base URL normalization was verified across all deployment formats:

```typescript
const apiBase = import.meta.env.VITE_API_BASE_URL || '';
const baseURL = apiBase ? (apiBase.endsWith('/api') ? apiBase : `${apiBase}/api`) : '/api';
```

- **Format A (`https://domain.com`):** Evaluates to `https://domain.com/api` (appends `/api` exactly once).
- **Format B (`https://domain.com/api`):** Evaluates to `https://domain.com/api` (prevents double `/api/api`).
- **Format C (Empty / Dev Mode):** Evaluates to `/api` (uses Vite proxy to `http://localhost:8000`).
- **Zero Localhost Leaks:** Production build contains no hardcoded localhost endpoints.

---

## 3. Security, Token & Route Guard Verification

1. **JWT Bearer Token Injection:**
   ```typescript
   api.interceptors.request.use((config) => {
     const token = localStorage.getItem('mirai_token');
     if (token && config.headers) {
       config.headers.Authorization = `Bearer ${token}`;
     }
     return config;
   });
   ```
2. **Automated 401 Unauthorized Expiry Handling:**
   ```typescript
   api.interceptors.response.use(
     (res) => res,
     (err) => {
       if (err.response?.status === 401) {
         localStorage.removeItem('mirai_token');
         localStorage.removeItem('mirai_user');
         if (window.location.pathname !== '/login') {
           window.location.href = '/login';
         }
       }
       return Promise.reject(err);
     }
   );
   ```
3. **Route Guards (`frontend/src/components/RouteGuards.tsx`):**
   - `RequireAuth`: Restricts protected application routes (`/`, `/markets`, `/regimes`, `/discovery`, `/library`, `/backtest`, `/portfolio`, `/assistant`, `/watchlist`, `/profile`, `/settings`). Redirects unauthenticated visitors to `/login`.
   - `GuestOnly`: Prevents authenticated users with active tokens from viewing `/login`, `/signup`, `/forgot-password`, or `/reset-password` (redirects directly to `/`).

4. **SPA Direct Link & Refresh Rewrites ([frontend/vercel.json](file:///c:/Users/srisa/OneDrive/Desktop/astraq/frontend/vercel.json)):**
   Wildcard rewrite rule (`/(.*)` &rarr; `/index.html`) prevents HTTP 404 errors on deep linking or browser refresh across all teammate pages.

---

## 4. Teammate UI & Design Fidelity

- **Zero Template Overwrites:** Teammate Pooja's layout, dark forest/emerald theme, font pairings, responsive sidebar, cards, and tables were strictly preserved.
- **Icons & Brand Consistency:** Kept Lucide React icons, responsive navigation pills, badge styling, and mobile drawer functionality.
