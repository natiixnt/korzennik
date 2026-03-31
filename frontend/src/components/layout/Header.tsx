import { Link, useLocation } from "react-router-dom";

export default function Header() {
  const location = useLocation();

  const links = [
    { to: "/", label: "Drzewo" },
    { to: "/persons", label: "Osoby" },
    { to: "/search", label: "Wyszukiwanie" },
  ];

  return (
    <header className="bg-[var(--color-primary)] text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold tracking-wide">
          Korzennik
        </Link>
        <nav className="flex gap-1">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`px-4 py-1.5 rounded-md text-sm transition-colors ${
                location.pathname === link.to
                  ? "bg-white/20 font-medium"
                  : "hover:bg-white/10"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
