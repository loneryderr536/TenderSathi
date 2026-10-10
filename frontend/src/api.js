const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const COMPANY_KEY = "tendersathi.companyId";
const TOKEN_KEY = "tendersathi.token";
const USER_KEY = "tendersathi.user";

/** The login session: a token for the backend and the user it belongs to. */
export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getUser() {
  try {
    const value = localStorage.getItem(USER_KEY);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

export function setSession(token, user) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    // Storage blocked (private window): the login lasts until the page is reloaded.
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {
    // Nothing was stored.
  }
}

/** Fired when the backend says the login has expired; the app then shows the login page. */
export const LOGGED_OUT_EVENT = "tendersathi:logged-out";

export function apiUrl(path) {
  return `${API_URL}${path}`;
}

/** Call the backend. Throws an Error whose message is the backend's `detail`. */
export async function request(path, { method = "GET", json, form } = {}) {
  // The free ngrok tunnel (public demo backend) shows a warning page to browsers unless this header is sent.
  const init = { method, headers: { "ngrok-skip-browser-warning": "true" } };
  const token = getToken();
  if (token) init.headers.Authorization = `Bearer ${token}`;
  if (json !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(json);
  } else if (form !== undefined) {
    init.body = form;
  }

  let response;
  try {
    response = await fetch(apiUrl(path), init);
  } catch {
    throw new Error("Cannot reach the server. Is the backend running?");
  }
  const body = await response.json().catch(() => null);
  if (response.status === 401 && token && !path.startsWith("/auth/")) {
    clearSession();
    window.dispatchEvent(new Event(LOGGED_OUT_EVENT));
  }
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${response.status})`;
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return body;
}

/** The tender page refreshes every 2 seconds while the agents are working. */
export function pollInterval(status) {
  return status === "running" ? 2000 : false;
}

export function getCompanyId() {
  try {
    const value = localStorage.getItem(COMPANY_KEY);
    return value ? Number(value) : null;
  } catch {
    return null;
  }
}

export function setCompanyId(id) {
  try {
    localStorage.setItem(COMPANY_KEY, String(id));
  } catch {
    // Storage blocked (private window): the profile still saves, it just isn't remembered.
  }
}

export function clearCompanyId() {
  try {
    localStorage.removeItem(COMPANY_KEY);
  } catch {
    // Storage blocked: nothing was remembered anyway.
  }
}

/** The remembered profile was deleted on the server (e.g. the database was reset). */
export function isCompanyGone(error) {
  return error?.status === 404 && error.message === "Company not found";
}
