interface Props {
  score: number;
  breakdown?: Record<string, number> | null;
}

export default function ConfidenceBadge({ score, breakdown }: Props) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.8
      ? "var(--color-confidence-high)"
      : score >= 0.5
      ? "var(--color-confidence-medium)"
      : "var(--color-confidence-low)";

  return (
    <div className="relative group">
      <div
        className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium text-white"
        style={{ backgroundColor: color }}
      >
        {pct}%
      </div>
      {breakdown && (
        <div className="absolute z-10 hidden group-hover:block bg-white border border-gray-200 rounded-lg shadow-lg p-3 w-56 top-full left-0 mt-1">
          <p className="text-xs font-semibold text-gray-600 mb-2">Szczegoly dopasowania:</p>
          {Object.entries(breakdown)
            .filter(([key]) => key !== "total")
            .map(([key, value]) => (
              <div key={key} className="flex justify-between text-xs py-0.5">
                <span className="text-gray-600">
                  {LABEL_MAP[key] ?? key}
                </span>
                <span className="font-mono">{Math.round(value * 100)}%</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

const LABEL_MAP: Record<string, string> = {
  surname: "Nazwisko",
  given_name: "Imie",
  birth_year: "Rok urodzenia",
  birth_place: "Miejsce urodzenia",
  father_name: "Imie ojca",
  mother_name: "Imie matki",
  source_reliability: "Wiarygodnosc zrodla",
};
