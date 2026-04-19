# Agrisense Setup

## Backend

Create a virtual environment from `agrs/backend`:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Frontend

Install and run the React app from `agrs/frontend`:

```powershell
npm install
npm run dev
```

Tailwind, Axios, and Recharts are already declared in `package.json`.
