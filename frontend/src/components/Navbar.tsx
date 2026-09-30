import { LogOut, Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

const links = [
  { to: "/chat", label: "Chat" },
  { to: "/history", label: "History" },
];

export function Navbar() {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  function handleLogout() {
    setMenuOpen(false);
    localStorage.removeItem("token");
    navigate("/login", { replace: true });
  }

  return (
    <>
      <nav className="sticky top-0 z-10 bg-white shadow-sm">
        <div className="mx-auto flex h-16 max-w-[1300px] items-center gap-3 px-4 sm:px-6 lg:px-8">
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-gray-700 hover:bg-gray-100 sm:hidden"
            aria-expanded={menuOpen}
            aria-controls="mobile-nav-sidebar"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>

          <h1 className="min-w-0 flex-1 truncate text-xl font-bold text-indigo-600 sm:flex-none">
            Car Dealer Assistant
          </h1>

          <div className="ml-0 hidden flex-1 items-center space-x-8 sm:ml-8 sm:flex">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `inline-flex items-center border-b-2 px-1 pt-1 text-sm font-medium ${
                    isActive
                      ? "border-indigo-500 text-gray-900"
                      : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="hidden sm:inline-flex ml-auto shrink-0 items-center rounded-md bg-red-400 px-3 py-2 text-sm font-medium text-white hover:bg-red-500 sm:px-4"
          >
            <LogOut size={16} className="text-white sm:mr-2" />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        </div>
      </nav>

      <div
        className={`fixed inset-0 z-40 bg-black/40 transition-opacity duration-200 sm:hidden ${
          menuOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={() => setMenuOpen(false)}
        aria-hidden
      />

      <aside
        id="mobile-nav-sidebar"
        className={`fixed inset-y-0 left-0 z-50 flex w-[min(18rem,85vw)] flex-col bg-white shadow-xl transition-transform duration-200 ease-out sm:hidden ${
          menuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-hidden={!menuOpen}
      >
        <div className="flex h-16 items-center border-b border-gray-100 px-4"></div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `rounded-lg px-3 py-3 text-sm font-medium ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-gray-700 hover:bg-gray-50"
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-100 p-3">
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-red-400 px-3 py-3 text-sm font-medium text-white hover:bg-red-500"
          >
            <LogOut size={18} />
            Sign out
          </button>
        </div>
      </aside>
    </>
  );
}
