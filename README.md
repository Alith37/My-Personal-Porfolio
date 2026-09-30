# Portfolio local development

The portfolio frontend uses Vite and the existing FastAPI app handles contact
form submissions. The original HTML, CSS, JavaScript, and image files remain at
the repository root so their existing paths and presentation are preserved.

## Requirements

- Node.js and npm
- Python with the packages in `backend/requirements.txt`
- A MongoDB Atlas connection string for contact form submissions

## Configure the backend

Copy `backend/.env.example` to `backend/.env` and set `MONGODB_URI` to your
MongoDB Atlas connection string. Keep `backend/.env` private; it is ignored by
Git.

## Run locally

Start the API in one terminal from the repository root:

```powershell
py -m uvicorn backend.main:app --reload --port 8000
```

Install frontend dependencies and start Vite in another terminal:

```powershell
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies requests under `/api` to
`http://127.0.0.1:8000`, so the contact form can continue to use the relative
URL `/api/contact`.

To create a production frontend build locally, run `npm run build`. This project
is not configured to deploy from this change.
