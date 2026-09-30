# AI Support Agent — Frontend

React + TypeScript + Vite chat UI for the car dealer assistant. It talks to the backend under `/api`.

---

## Prerequisites

- **Node.js** (current LTS is a good choice) and **npm** (or another client compatible with `package.json`).

---

## Frontend setup

1. Open a terminal in this directory (`frontend/`), next to `package.json`.

2. **Environment file**

   ```bash
   cp example.env .env
   ```

   Edit `.env` if your API is not on the default URL.

   | Variable            | Purpose                                                                                                               |
   | ------------------- | --------------------------------------------------------------------------------------------------------------------- |
   | `VITE_API_BASE_URL` | Base URL for the backend API (must include the `/api` prefix). Default in `example.env`: `http://127.0.0.1:8000/api`. |

   Vite reads `.env`, `.env.local`, and mode-specific files. Use `.env.local` for machine-specific overrides if you prefer (see [Vite env variables](https://vite.dev/guide/env-and-mode.html)).

3. **Install dependencies**

   ```bash
   npm install
   ```

---

## Run the frontend (development)

With the **backend** running (see the root [README.md](../README.md)), start the dev server:

```bash
npm run dev
```

By default Vite serves the app at **http://localhost:5173** (or the next free port). Ensure `VITE_API_BASE_URL` matches where your API is listening and that backend `CORS_ORIGINS` includes this origin.

---

## Other scripts

| Command           | Description                                |
| ----------------- | ------------------------------------------ |
| `npm run build`   | Typecheck and production build to `dist/`. |
| `npm run preview` | Preview the production build locally.      |
| `npm run lint`    | Run ESLint.                                |

---

## Stack notes

- **Routing:** `react-router-dom`
- **Data / HTTP:** `@tanstack/react-query`, `axios`
- **Styling:** Tailwind CSS v4

The template originally shipped with extra ESLint / React Compiler notes; this README focuses on this repo’s setup. For React Compiler details, see the [React docs](https://react.dev/learn/react-compiler).
