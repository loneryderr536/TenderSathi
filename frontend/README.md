# Frontend

React (JavaScript) + Vite + Tailwind CSS, with React Router and TanStack Query.

```bash
npm install
npm run dev      # http://localhost:5173 (expects the backend on http://localhost:8000)
npm test         # Vitest + Testing Library
npm run build
```

Set `VITE_API_URL` to point at a different backend.

Pages: Tender Inbox (`/`), Business Profile (`/profile`), Tender Detail with the live agent log
(`/tenders/:id`), Approve & Export (`/tenders/:id/approve`).
