import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { vi } from "vitest";

/** Mock fetch with a route table: { "GET /tenders": body | (init) => body | {status, body} }. */
export function mockApi(routes) {
  const calls = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init = {}) => {
    const method = init.method || "GET";
    const path = new URL(url).pathname;
    calls.push({ method, path, init });
    const handler = routes[`${method} ${path}`];
    if (handler === undefined) return new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 });
    let result = typeof handler === "function" ? handler(init) : handler;
    if (!(result && result.status && "body" in result)) result = { status: 200, body: result };
    return new Response(JSON.stringify(result.body), { status: result.status });
  });
  return calls;
}

export function renderPage(element, { path = "/", route = "/" } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={element} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...view, client };
}
