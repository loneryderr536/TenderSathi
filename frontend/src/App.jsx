import { useEffect } from "react";
import { NavLink, Route, Routes, useLocation, useSearchParams } from "react-router";
import { setCompanyId } from "./api";
import AdminPage from "./pages/AdminPage";
import ApprovePage from "./pages/ApprovePage";
import GovPage from "./pages/GovPage";
import GovTenderPage from "./pages/GovTenderPage";
import InboxPage from "./pages/InboxPage";
import ProfilePage from "./pages/ProfilePage";
import TenderPage from "./pages/TenderPage";

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `rounded-md px-2 py-2 text-sm font-medium sm:px-3 ${isActive ? "bg-brand-700 text-white" : "text-brand-100 hover:bg-brand-700/60"}`
      }
    >
      {children}
    </NavLink>
  );
}

/** Three views of one platform: the business owner, the government buyer, and the platform team. */
const ROLES = [
  { key: "business", label: "Business", to: "/" },
  { key: "gov", label: "Government", to: "/gov" },
  { key: "admin", label: "Platform", to: "/admin" },
];

function roleOf(pathname) {
  if (pathname.startsWith("/gov")) return "gov";
  if (pathname.startsWith("/admin")) return "admin";
  return "business";
}

function RoleSwitcher({ role }) {
  return (
    <div className="flex rounded-lg bg-brand-700/50 p-0.5" role="group" aria-label="View as">
      {ROLES.map((r) => (
        <NavLink
          key={r.key}
          to={r.to}
          aria-current={role === r.key ? "true" : undefined}
          className={`rounded-md px-2.5 py-1 text-xs font-semibold sm:px-3 ${role === r.key ? "bg-white text-brand-900" : "text-brand-100 hover:text-white"}`}
        >
          {r.label}
        </NavLink>
      ))}
    </div>
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

const FOOTER = {
  business: "TenderSathi never contacts the government and never submits for you. You approve, you price, you submit.",
  gov: "Insights show totals and anonymous labels only; no business's profile is shared with buyers.",
  admin: "Platform view: agent health, Scout activity and how often owners agree with the agents.",
};

export default function App() {
  useCompanyFromLink();
  const role = roleOf(useLocation().pathname);
  return (
    <div className="min-h-screen">
      <header className="bg-brand-900">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
          <div className="flex items-center gap-3">
            <NavLink to="/" className="text-lg font-semibold text-white">TenderSathi</NavLink>
            <RoleSwitcher role={role} />
          </div>
          <nav className="flex gap-1">
            {role === "business" && (
              <>
                <NavItem to="/">Tender inbox</NavItem>
                <NavItem to="/profile">Business profile</NavItem>
              </>
            )}
            {role === "gov" && <NavItem to="/gov">Buyer dashboard</NavItem>}
            {role === "admin" && <NavItem to="/admin">Platform health</NavItem>}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Routes>
          <Route path="/" element={<InboxPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/tenders/:id" element={<TenderPage />} />
          <Route path="/tenders/:id/approve" element={<ApprovePage />} />
          <Route path="/gov" element={<GovPage />} />
          <Route path="/gov/tenders/:id" element={<GovTenderPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </main>
      <footer className="mx-auto max-w-5xl px-4 pb-8 text-xs text-stone-500">{FOOTER[role]}</footer>
    </div>
  );
}
