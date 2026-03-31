import { useDiscovery } from "../../hooks/useDiscovery";
import { usePersons } from "../../hooks/usePersons";
import { useRef, useEffect } from "react";

export default function DiscoveryPanel() {
  const { start, stop, progress, activeRunId } = useDiscovery();
  const { data: persons } = usePersons();
  const logRef = useRef<HTMLDivElement>(null);

  const p = progress.data;
  const isRunning = p?.status === "running";

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [p?.log?.length]);

  const handleStart = () => {
    start.mutate({});
  };

  const handleStop = () => {
    if (activeRunId) {
      stop.mutate(activeRunId);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-[var(--color-primary)]">
            Automatyczne odkrywanie przodkow
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Przeszukuje wszystkie zrodla, waliduje krzyzowo i buduje drzewo automatycznie
          </p>
        </div>
      </div>

      {/* Start controls */}
      {!isRunning && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <p className="text-sm text-gray-600">
            System przeszuka {persons?.length ?? 0} osob we wszystkich 8 zrodlach,
            automatycznie potwierdzi wyniki o pewnosci &gt;75%,
            odkryje nowych przodkow i przeszuka rekurencyjnie do 10 pokolen wstecz.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleStart}
              disabled={start.isPending || !persons?.length}
              className="px-6 py-2 bg-[var(--color-primary)] text-white rounded-lg hover:bg-[var(--color-primary-light)] transition-colors disabled:opacity-50 font-medium"
            >
              {start.isPending ? "Uruchamianie..." : "Szukaj przodkow"}
            </button>
          </div>
        </div>
      )}

      {/* Progress */}
      {p && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
          {/* Status bar */}
          <div className="flex items-center gap-3">
            <div
              className={`w-3 h-3 rounded-full ${
                p.status === "running"
                  ? "bg-yellow-400 animate-pulse"
                  : p.status === "completed"
                  ? "bg-green-500"
                  : p.status === "failed"
                  ? "bg-red-500"
                  : "bg-gray-400"
              }`}
            />
            <span className="font-medium capitalize">
              {p.status === "running"
                ? "W trakcie..."
                : p.status === "completed"
                ? "Zakonczone"
                : p.status === "stopped"
                ? "Zatrzymane"
                : p.status === "failed"
                ? "Blad"
                : p.status}
            </span>
            {isRunning && (
              <button
                onClick={handleStop}
                className="ml-auto px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
              >
                Zatrzymaj
              </button>
            )}
          </div>

          {/* Progress bar */}
          {p.total_persons > 0 && (
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-[var(--color-primary)] h-2 rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(100, (p.searched_persons / p.total_persons) * 100)}%`,
                }}
              />
            </div>
          )}

          {/* Stats grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard label="Przeszukano" value={p.searched_persons} total={p.total_persons} />
            <StatCard label="Znalezione" value={p.matches_found} />
            <StatCard label="Potwierdzone" value={p.auto_confirmed} highlight="green" />
            <StatCard label="Odkryte osoby" value={p.new_persons_created} highlight="blue" />
            <StatCard label="Walidacja krzyzowa" value={p.cross_validated} />
            <StatCard label="Wzbogacone" value={p.persons_enriched} />
            <StatCard label="Pokolenie" value={p.current_depth} />
            <StatCard label="Bledy" value={p.errors.length} highlight={p.errors.length > 0 ? "red" : undefined} />
          </div>

          {/* Log */}
          {p.log.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Dziennik:</h4>
              <div
                ref={logRef}
                className="bg-gray-50 rounded border border-gray-100 p-3 max-h-64 overflow-y-auto font-mono text-xs space-y-0.5"
              >
                {p.log.map((entry, i) => (
                  <div
                    key={i}
                    className={`${
                      entry.startsWith("  Potwierdzono")
                        ? "text-green-700"
                        : entry.startsWith("  Brak")
                        ? "text-gray-400"
                        : entry.startsWith("Zakonczono")
                        ? "text-[var(--color-primary)] font-bold"
                        : "text-gray-600"
                    }`}
                  >
                    {entry}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Errors */}
          {p.errors.length > 0 && (
            <div className="bg-red-50 rounded p-3">
              <h4 className="text-sm font-medium text-red-700 mb-1">Bledy:</h4>
              {p.errors.map((err, i) => (
                <p key={i} className="text-xs text-red-600">{err}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  total,
  highlight,
}: {
  label: string;
  value: number;
  total?: number;
  highlight?: "green" | "blue" | "red";
}) {
  const colors = {
    green: "text-green-600",
    blue: "text-blue-600",
    red: "text-red-600",
  };

  return (
    <div className="bg-gray-50 rounded p-2 text-center">
      <div className={`text-lg font-bold ${highlight ? colors[highlight] : "text-gray-900"}`}>
        {value}
        {total !== undefined && <span className="text-gray-400 text-sm">/{total}</span>}
      </div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}
