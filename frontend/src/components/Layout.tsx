import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../features/auth/authStore";
import NotificationBell from "./NotificationBell";

interface Props { children: React.ReactNode; }

export default function Layout({ children }: Props) {
  const { token, fullName, role, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-brand-900 text-white">
        <nav className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between" aria-label="Main navigation">
          <Link to="/" className="font-bold text-lg tracking-tight">
            🚗 DMV Registration Assistant
          </Link>
          <div className="flex items-center gap-4 text-sm">
            {token ? (
              <>
                <span className="text-blue-200 hidden sm:inline">Signed in as {fullName}</span>
                {role === "staff" || role === "admin" ? (
                  <Link to="/staff" className="hover:underline">Staff Dashboard</Link>
                ) : (
                  <Link to="/dashboard" className="hover:underline">My Cases</Link>
                )}
                <NotificationBell />
                <button onClick={handleLogout} className="hover:underline">Sign out</button>
              </>
            ) : (
              <>
                <Link to="/login" className="hover:underline">Sign in</Link>
                <Link to="/register" className="hover:underline font-semibold">Get started</Link>
              </>
            )}
          </div>
        </nav>
      </header>
      <main className="flex-1 max-w-6xl mx-auto px-4 py-8 w-full">
        {children}
      </main>
      <footer className="bg-gray-100 border-t border-gray-200 text-center py-4 text-xs text-gray-500">
        Educational prototype · Not affiliated with the SCDMV ·
        Queue, appointment, tax, and ownership data are simulated.
      </footer>
    </div>
  );
}
