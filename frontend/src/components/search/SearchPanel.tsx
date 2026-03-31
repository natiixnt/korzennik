import { useConfirmMatch, useRejectMatch, useSearchResults, useSearchStatus, useTriggerSearch } from "../../hooks/useSearch";
import MatchCard from "./MatchCard";

interface Props {
  personId: string | null;
  personName?: string;
}

export default function SearchPanel({ personId, personName }: Props) {
  const trigger = useTriggerSearch();
  const { data: status } = useSearchStatus(personId);
  const { data: results } = useSearchResults(personId);
  const confirm = useConfirmMatch();
  const reject = useRejectMatch();

  if (!personId) {
    return (
      <div className="p-6 text-center text-gray-500">
        Wybierz osobe z listy, aby wyszukac zapisy
      </div>
    );
  }

  const isSearching = status?.some(
    (t) => t.status === "queued" || t.status === "running"
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">
          Wyniki dla: {personName ?? personId}
        </h3>
        <button
          onClick={() => trigger.mutate({ personId })}
          disabled={isSearching || trigger.isPending}
          className="px-4 py-2 bg-[var(--color-primary)] text-white rounded-md hover:bg-[var(--color-primary-light)] transition-colors disabled:opacity-50"
        >
          {isSearching ? "Szukanie..." : "Szukaj"}
        </button>
      </div>

      {/* Search status */}
      {status && status.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {status.map((task) => (
            <div
              key={task.id}
              className={`text-xs px-2 py-1 rounded-full ${
                task.status === "completed"
                  ? "bg-green-100 text-green-700"
                  : task.status === "running"
                  ? "bg-yellow-100 text-yellow-700"
                  : task.status === "failed"
                  ? "bg-red-100 text-red-700"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {task.source_name}: {task.status}
              {task.result_count > 0 && ` (${task.result_count})`}
            </div>
          ))}
        </div>
      )}

      {/* Results */}
      {results && results.length > 0 ? (
        <div className="space-y-3">
          {results.map((match) => (
            <MatchCard
              key={match.id}
              match={match}
              onConfirm={(id) => confirm.mutate(id)}
              onReject={(id) => reject.mutate(id)}
            />
          ))}
        </div>
      ) : (
        !isSearching && (
          <p className="text-gray-500 text-center py-4">
            Brak wynikow. Kliknij "Szukaj" aby rozpoczac wyszukiwanie.
          </p>
        )
      )}
    </div>
  );
}
