import { useEffect, useRef, useLayoutEffect, useState } from "react";

export interface ContextMenuItem {
  label: string;
  onClick: () => void;
  danger?: boolean;
  divider?: boolean;
}

interface Props {
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
}

export default function ContextMenu({ x, y, items, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ x, y });

  // Adjust position to stay within viewport
  useLayoutEffect(() => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const pad = 8;
    let nx = x;
    let ny = y;
    if (nx + rect.width > window.innerWidth - pad) {
      nx = x - rect.width;
    }
    if (ny + rect.height > window.innerHeight - pad) {
      ny = y - rect.height;
    }
    if (nx < pad) nx = pad;
    if (ny < pad) ny = pad;
    setPos({ x: nx, y: ny });
  }, [x, y]);

  useEffect(() => {
    const handleAny = () => onClose();
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    // Close on any mousedown OR right-click anywhere outside
    const handleMouseDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };
    // Also close on contextmenu (right-click) outside
    const handleContextMenu = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };
    // Close on scroll
    const handleScroll = () => onClose();

    document.addEventListener("mousedown", handleMouseDown, true);
    document.addEventListener("contextmenu", handleContextMenu, true);
    document.addEventListener("keydown", handleEsc);
    window.addEventListener("scroll", handleScroll, true);
    window.addEventListener("resize", handleAny);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown, true);
      document.removeEventListener("contextmenu", handleContextMenu, true);
      document.removeEventListener("keydown", handleEsc);
      window.removeEventListener("scroll", handleScroll, true);
      window.removeEventListener("resize", handleAny);
    };
  }, [onClose]);

  return (
    <div
      ref={ref}
      style={{ position: "fixed", left: pos.x, top: pos.y, zIndex: 1000 }}
      className="animate-in"
    >
      <div className="bg-white rounded-lg shadow-2xl border border-gray-200/80 py-1.5 min-w-[180px]">
        {items.map((item, i) =>
          item.divider ? (
            <div key={i} className="border-t border-gray-100 my-1" />
          ) : (
            <button
              key={i}
              onClick={() => {
                item.onClick();
                onClose();
              }}
              className={`w-full text-left px-3 py-[7px] text-[13px] transition-colors ${
                item.danger
                  ? "text-red-600 hover:bg-red-50"
                  : "text-gray-700 hover:bg-[var(--color-primary)]/5 hover:text-[var(--color-primary)]"
              }`}
            >
              {item.label}
            </button>
          )
        )}
      </div>
    </div>
  );
}
