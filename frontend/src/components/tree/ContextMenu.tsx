import { useEffect, useRef, useLayoutEffect, useState } from "react";

export interface ContextMenuItem {
  label: string;
  icon?: string;
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
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    // Use capture so we close before other handlers
    document.addEventListener("mousedown", handleClick, true);
    document.addEventListener("keydown", handleEsc);
    return () => {
      document.removeEventListener("mousedown", handleClick, true);
      document.removeEventListener("keydown", handleEsc);
    };
  }, [onClose]);

  return (
    <div
      ref={ref}
      style={{ position: "fixed", left: pos.x, top: pos.y, zIndex: 1000 }}
      className="animate-in"
    >
      <div className="bg-white rounded-lg shadow-2xl border border-gray-200/80 py-1.5 min-w-[180px] backdrop-blur-sm">
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
              className={`w-full text-left px-3 py-[7px] text-[13px] flex items-center gap-2.5 transition-colors ${
                item.danger
                  ? "text-red-600 hover:bg-red-50"
                  : "text-gray-700 hover:bg-[var(--color-primary)]/5 hover:text-[var(--color-primary)]"
              }`}
            >
              {item.icon && (
                <span className="w-4 text-center text-xs opacity-60">{item.icon}</span>
              )}
              {item.label}
            </button>
          )
        )}
      </div>
    </div>
  );
}
