const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const COMPANY_KEY = "tendersathi.companyId";

export function apiUrl(path) {
  return `${API_URL}${path}`;
}

/** Call the backend. Throws an Error whose message is the backend's `detail`. */
export async function request(path, { method = "GET", json, form } = {}) {
  const init = { method };
  if (json !== undefined) {
    init.headers = { "Content-Type": "application/json" };
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
