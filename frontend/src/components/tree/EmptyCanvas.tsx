interface Props {
  onAdd: () => void;
}

export default function EmptyCanvas({ onAdd }: Props) {
  return (
    <div className="h-full flex items-center justify-center bg-[var(--color-bg)]">
      <div className="text-center">
        {/* Dotted grid background hint */}
        <div className="relative">
          {/* Large + button */}
          <button
            onClick={onAdd}
            className="group relative w-24 h-24 rounded-2xl border-2 border-dashed border-gray-300 hover:border-[var(--color-primary)] hover:bg-[var(--color-primary)]/5 transition-all duration-200 flex items-center justify-center"
          >
            <span className="text-4xl text-gray-300 group-hover:text-[var(--color-primary)] transition-colors">
              +
            </span>
          </button>
        </div>
        <p className="mt-4 text-gray-400 text-sm">
          Dodaj pierwsza osobe
        </p>
        <p className="mt-1 text-gray-300 text-xs">
          lub kliknij prawym przyciskiem w dowolnym miejscu
        </p>
      </div>
    </div>
  );
}
