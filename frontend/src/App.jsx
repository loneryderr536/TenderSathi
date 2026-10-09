import { useEffect } from "react";
import { NavLink, Route, Routes, useSearchParams } from "react-router";
import { setCompanyId } from "./api";
import ApprovePage from "./pages/ApprovePage";
import InboxPage from "./pages/InboxPage";
import ProfilePage from "./pages/ProfilePage";
import TenderPage from "./pages/TenderPage";

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-brand-700 text-white" : "text-brand-100 hover:bg-brand-700/60"}`
      }
    >
      {children}
    </NavLink>
  );
}

/** The demo loader prints a link with ?company=<id>; opening it once makes the site use that profile. */
function useCompanyFromLink() {
  const [params, setParams] = useSearchParams();
  const company = params.get("company");
  useEffect(() => {
    if (company === null) return;
    if (/^\d+$/.test(company)) setCompanyId(Number(company));
    params.delete("company");
    setParams(params, { replace: true });
  }, [company, params, setParams]);
}

export default function App() {
  useCompanyFromLink();
  return (
    <div className="min-h-screen">
      <header className="bg-brand-900">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <NavLink to="/" className="text-lg font-semibold text-white">
            TenderSathi
          </NavLink>
          <nav className="flex gap-1">
            <NavItem to="/">Tender inbox</NavItem>
            <NavItem to="/profile">Business profile</NavItem>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Routes>
          <Route path="/" element={<InboxPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/tenders/:id" element={<TenderPage />} />
          <Route path="/tenders/:id/approve" element={<ApprovePage />} />
        </Routes>
      </main>
      <footer className="mx-auto max-w-5xl px-4 pb-8 text-xs text-stone-500">
        TenderSathi never contacts the government and never submits for you. You approve, you price, you submit.
      </footer>
    </div>
  );
}
