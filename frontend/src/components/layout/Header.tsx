import { Link, useLocation } from "react-router-dom";

export default function Header() {
  const location = useLocation();

  const links = [
    { to: "/", label: "Drzewo" },
    { to: "/persons", label: "Osoby" },
    { to: "/search", label: "Wyszukiwanie" },
  ];

  return (
    <header className="bg-[var(--color-primary)] text-white">
      <div className="px-4 py-2 flex items-center justify-between">
        <Link to="/" className="text-lg font-bold tracking-wide">
          Korzennik
        </Link>
        <nav className="flex gap-0.5">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                location.pathname === link.to
                  ? "bg-white/20 font-medium"
                  : "hover:bg-white/10 text-white/80"
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
