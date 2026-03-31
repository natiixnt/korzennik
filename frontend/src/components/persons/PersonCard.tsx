import type { Person } from "../../types/person";

interface Props {
  person: Person;
  onSelect?: (id: string) => void;
  onSearch?: (id: string) => void;
  selected?: boolean;
}

export default function PersonCard({ person, onSelect, onSearch, selected }: Props) {
  const primaryName = person.names.find((n) => n.is_primary) ?? person.names[0];
  const birth = person.events.find((e) => e.event_type === "birth");
  const death = person.events.find((e) => e.event_type === "death");

  const displayName = primaryName
    ? `${primaryName.given_name ?? ""} ${primaryName.surname ?? ""}`.trim()
    : "Nieznane imie";

  const dates = [birth?.date_text, death?.date_text].filter(Boolean).join(" - ");
  const places = [birth?.place_text, death?.place_text].filter(Boolean);

  return (
    <div
      className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
        selected
          ? "border-[var(--color-primary)] bg-green-50 shadow"
          : "border-gray-200 bg-white"
      }`}
      onClick={() => onSelect?.(person.id)}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span
              className={`inline-block w-3 h-3 rounded-full ${
                person.gender === "M"
                  ? "bg-blue-400"
                  : person.gender === "F"
                  ? "bg-pink-400"
                  : "bg-gray-300"
              }`}
            />
            <h4 className="font-semibold text-[var(--color-text)]">{displayName}</h4>
          </div>
          {dates && (
            <p className="text-sm text-[var(--color-text-muted)] mt-1">{dates}</p>
          )}
          {places.map((p, i) => (
            <p key={i} className="text-xs text-[var(--color-text-muted)]">
              {p}
            </p>
          ))}
          <span
            className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full ${
              person.origin === "user_entered"
                ? "bg-green-100 text-green-700"
                : person.origin === "confirmed_match"
                ? "bg-blue-100 text-blue-700"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            {person.origin === "user_entered"
              ? "Wprowadzony"
              : person.origin === "confirmed_match"
              ? "Ze zrodla"
              : person.origin}
          </span>
        </div>
        {onSearch && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSearch(person.id);
            }}
            className="ml-2 px-3 py-1 text-sm bg-[var(--color-secondary)] text-white rounded hover:opacity-80 transition-opacity"
          >
            Szukaj
          </button>
        )}
      </div>
    </div>
  );
}
