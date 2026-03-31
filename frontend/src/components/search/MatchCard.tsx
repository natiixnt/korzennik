import type { SourceMatch } from "../../types/search";
import ConfidenceBadge from "./ConfidenceBadge";

interface Props {
  match: SourceMatch;
  onConfirm: (id: number) => void;
  onReject: (id: number) => void;
}

export default function MatchCard({ match, onConfirm, onReject }: Props) {
  const displayName = [match.given_name, match.surname].filter(Boolean).join(" ");

  return (
    <div className="p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h4 className="font-semibold">{displayName || "Brak imienia"}</h4>
            <ConfidenceBadge
              score={match.confidence_score}
              breakdown={match.confidence_breakdown}
            />
            <span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full text-gray-600">
              {match.source_name}
            </span>
          </div>

          <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
            {match.birth_date && (
              <div>
                <span className="text-gray-500">Urodzenie:</span>{" "}
                {match.birth_date}
              </div>
            )}
            {match.birth_place && (
              <div>
                <span className="text-gray-500">Miejsce ur.:</span>{" "}
                {match.birth_place}
              </div>
            )}
            {match.death_date && (
              <div>
                <span className="text-gray-500">Smierc:</span>{" "}
                {match.death_date}
              </div>
            )}
            {match.death_place && (
              <div>
                <span className="text-gray-500">Miejsce sm.:</span>{" "}
                {match.death_place}
              </div>
            )}
            {match.father_name && (
              <div>
                <span className="text-gray-500">Ojciec:</span>{" "}
                {match.father_name}
              </div>
            )}
            {match.mother_name && (
              <div>
                <span className="text-gray-500">Matka:</span>{" "}
                {match.mother_name}
              </div>
            )}
          </div>

          {match.source_url && (
            <a
              href={match.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-2 text-sm text-blue-600 hover:underline"
            >
              Zobacz w zrodle
            </a>
          )}
        </div>
      </div>

      {match.status === "pending" && (
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => onConfirm(match.id)}
            className="px-4 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
          >
            Potwierdz
          </button>
          <button
            onClick={() => onReject(match.id)}
            className="px-4 py-1.5 bg-red-100 text-red-700 text-sm rounded hover:bg-red-200 transition-colors"
          >
            Odrzuc
          </button>
        </div>
      )}
      {match.status === "confirmed" && (
        <span className="inline-block mt-2 text-sm text-green-600 font-medium">
          Potwierdzony
        </span>
      )}
      {match.status === "rejected" && (
        <span className="inline-block mt-2 text-sm text-red-500">
          Odrzucony
        </span>
      )}
    </div>
  );
}
