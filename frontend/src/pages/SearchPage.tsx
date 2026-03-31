import { useState } from "react";
import { usePersons } from "../hooks/usePersons";
import PersonCard from "../components/persons/PersonCard";
import SearchPanel from "../components/search/SearchPanel";

export default function SearchPage() {
  const { data: persons } = usePersons();
  const [searchingId, setSearchingId] = useState<string | null>(null);

  const searchingPerson = persons?.find((p) => p.id === searchingId);
  const displayName = searchingPerson?.names[0]
    ? `${searchingPerson.names[0].given_name ?? ""} ${searchingPerson.names[0].surname ?? ""}`.trim()
    : undefined;

  return (
    <div className="h-full flex">
      {/* Person list */}
      <div className="w-80 border-r border-gray-200 bg-gray-50 overflow-y-auto p-4 space-y-3">
        <h2 className="text-lg font-bold text-[var(--color-primary)] mb-2">
          Wybierz osobe
        </h2>
        {persons?.map((person) => (
          <PersonCard
            key={person.id}
            person={person}
            selected={person.id === searchingId}
            onSelect={(id) => setSearchingId(id)}
          />
        ))}
        {persons?.length === 0 && (
          <p className="text-gray-400 text-center py-8">
            Najpierw dodaj osoby na stronie "Osoby"
          </p>
        )}
      </div>

      {/* Search results */}
      <div className="flex-1 overflow-y-auto p-6">
        <SearchPanel personId={searchingId} personName={displayName} />
      </div>
    </div>
  );
}
