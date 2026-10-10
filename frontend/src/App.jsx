import { useEffect } from "react";
import { Navigate, NavLink, Route, Routes, useLocation, useSearchParams } from "react-router";
import { setCompanyId } from "./api";
import { AuthProvider, HOME, VIEWS, useAuth } from "./auth";
import AdminPage from "./pages/AdminPage";
import ApprovePage from "./pages/ApprovePage";
import GovPage from "./pages/GovPage";
import GovTenderPage from "./pages/GovTenderPage";
import InboxPage from "./pages/InboxPage";
import LoginPage from "./pages/LoginPage";
import PrivatePage from "./pages/PrivatePage";
import PrivateRfqPage from "./pages/PrivateRfqPage";
import ProfilePage from "./pages/ProfilePage";
import SignupPage from "./pages/SignupPage";
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
  { key: "private", label: "Private", to: "/private" },
  { key: "admin", label: "Platform", to: "/admin" },
];

function roleOf(pathname) {
  if (pathname.startsWith("/gov")) return "gov";
  if (pathname.startsWith("/admin")) return "admin";
  if (pathname.startsWith("/private")) return "private";
  return "business";
}

function RoleSwitcher({ role, allowed }) {
  if (allowed.length < 2) return null;
  return (
    <div className="flex rounded-lg bg-brand-700/50 p-0.5" role="group" aria-label="View as">
      {ROLES.filter((r) => allowed.includes(r.key)).map((r) => (
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
  private: "Every request carries an advance of 25% to 50% of the order value, paid when you place the order.",
  admin: "Platform view: agent health, Scout activity and how often owners agree with the agents.",
};

const ROLE_NAME = { business: "Business", government: "Government", private: "Private owner", platform: "Platform" };

function LoggedOut() {
  return (
    <div className="min-h-screen">
      <header className="bg-brand-900">
        <div className="mx-auto max-w-5xl px-4 py-3">
          <span className="text-lg font-semibold text-white">TenderSathi</span>
          <span className="ml-3 text-sm text-brand-100">Government tenders, made winnable for small businesses</span>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Routes>
          <Route path="/signup" element={<SignupPage />} />
          <Route path="*" element={<LoginPage />} />
        </Routes>
      </main>
    </div>
  );
}

function Shell() {
  useCompanyFromLink();
  const { user, logOut } = useAuth();
  const { pathname } = useLocation();
  if (!user) return <LoggedOut />;
  const allowed = VIEWS[user.role] || [];
  const role = roleOf(pathname);
  if (pathname === "/login" || pathname === "/signup" || !allowed.includes(role)) {
    return <Navigate to={HOME[user.role]} replace />;
  }
  return (
    <div className="min-h-screen">
      <header className="bg-brand-900">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
          <div className="flex items-center gap-3">
            <NavLink to={HOME[user.role]} className="text-lg font-semibold text-white">TenderSathi</NavLink>
            <RoleSwitcher role={role} allowed={allowed} />
          </div>
          <div className="flex flex-wrap items-center gap-2">
          <nav className="flex gap-1">
            {role === "business" && (
              <>
                <NavItem to="/">Tender inbox</NavItem>
                <NavItem to="/profile">Business profile</NavItem>
              </>
            )}
            {role === "gov" && <NavItem to="/gov">Buyer dashboard</NavItem>}
            {role === "private" && <NavItem to="/private">Owner dashboard</NavItem>}
            {role === "admin" && <NavItem to="/admin">Platform health</NavItem>}
          </nav>
          <span className="hidden text-xs text-brand-100 sm:inline" title={user.email}>
            {user.name} · {ROLE_NAME[user.role]}
          </span>
          <button type="button" onClick={logOut} className="rounded-md px-2 py-2 text-sm font-medium text-brand-100 hover:bg-brand-700/60">
            Log out
          </button>
          </div>
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
          <Route path="/private" element={<PrivatePage />} />
          <Route path="/private/rfq/:id" element={<PrivateRfqPage />} />
          <Route path="/private/drafts/:id" element={<GovTenderPage back="/private" backLabel="Owner dashboard" />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </main>
      <footer className="mx-auto max-w-5xl px-4 pb-8 text-xs text-stone-500">{FOOTER[role]}</footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  );
}
