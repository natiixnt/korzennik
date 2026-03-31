import { useState } from "react";
import { usePersons } from "../hooks/usePersons";
import PersonCard from "../components/persons/PersonCard";
import PersonForm from "../components/persons/PersonForm";
import SearchPanel from "../components/search/SearchPanel";
import { createRelationship } from "../api/relationships";

export default function PersonsPage() {
  const { data: persons, isLoading } = usePersons();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [searchingId, setSearchingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [linkMode, setLinkMode] = useState<{
    personId: string;
    role: "father" | "mother" | "child" | "spouse";
  } | null>(null);

  const selectedPerson = persons?.find((p) => p.id === selectedId);
  const searchingPerson = persons?.find((p) => p.id === searchingId);
  const searchName = searchingPerson?.names[0]
    ? `${searchingPerson.names[0].given_name ?? ""} ${searchingPerson.names[0].surname ?? ""}`.trim()
    : undefined;

  const handleLink = async (targetId: string) => {
    if (!linkMode) return;

    if (linkMode.role === "father" || linkMode.role === "mother") {
      await createRelationship({
        person1_id: targetId,
        person2_id: linkMode.personId,
        rel_type: "parent_child",
      });
    } else if (linkMode.role === "child") {
      await createRelationship({
        person1_id: linkMode.personId,
        person2_id: targetId,
        rel_type: "parent_child",
      });
    } else if (linkMode.role === "spouse") {
      await createRelationship({
        person1_id: linkMode.personId,
        person2_id: targetId,
        rel_type: "spouse",
      });
    }
    setLinkMode(null);
  };

  return (
    <div className="h-full flex">
      {/* Person list */}
      <div className="w-96 border-r border-gray-200 bg-gray-50 overflow-y-auto p-4 space-y-3">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-bold text-[var(--color-primary)]">Osoby</h2>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-3 py-1 text-sm bg-[var(--color-primary)] text-white rounded hover:bg-[var(--color-primary-light)]"
          >
            + Dodaj
          </button>
        </div>

        {showForm && (
          <PersonForm onCreated={() => setShowForm(false)} />
        )}

        {isLoading && <p className="text-gray-400">Ladowanie...</p>}

        {persons?.map((person) => (
          <PersonCard
            key={person.id}
            person={person}
            selected={person.id === selectedId}
            onSelect={(id) => setSelectedId(id)}
            onSearch={(id) => setSearchingId(id)}
          />
        ))}

        {persons?.length === 0 && !showForm && (
          <p className="text-gray-400 text-center py-8">
            Brak osob. Dodaj pierwsza osobe!
          </p>
        )}
      </div>

      {/* Detail / actions panel */}
      <div className="flex-1 overflow-y-auto p-6">
        {selectedPerson && (
          <div className="max-w-2xl space-y-6">
            <div>
              <h2 className="text-2xl font-bold">
                {selectedPerson.names[0]?.given_name}{" "}
                {selectedPerson.names[0]?.surname}
              </h2>
              <p className="text-gray-500">
                {selectedPerson.gender === "M" ? "Mezczyzna" : selectedPerson.gender === "F" ? "Kobieta" : "Nieznana plec"}
              </p>
            </div>

            {selectedPerson.events.map((event) => (
              <div key={event.id} className="bg-gray-50 p-3 rounded">
                <span className="font-medium capitalize">{event.event_type}:</span>{" "}
                {event.date_text && <span>{event.date_text}</span>}
                {event.place_text && <span> - {event.place_text}</span>}
              </div>
            ))}

            {/* Relationship links */}
            <div className="flex gap-2 flex-wrap">
              {(["father", "mother", "child", "spouse"] as const).map((role) => (
                <button
                  key={role}
                  onClick={() =>
                    setLinkMode({ personId: selectedPerson.id, role })
                  }
                  className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100"
                >
                  + Dodaj{" "}
                  {role === "father"
                    ? "ojca"
                    : role === "mother"
                    ? "matke"
                    : role === "child"
                    ? "dziecko"
                    : "malzonka"}
                </button>
              ))}
            </div>

            {linkMode && (
              <div className="bg-yellow-50 p-4 rounded border border-yellow-200">
                <p className="text-sm mb-2">
                  Wybierz osobe z listy po lewej, ktora jest{" "}
                  {linkMode.role === "father"
                    ? "ojcem"
                    : linkMode.role === "mother"
                    ? "matka"
                    : linkMode.role === "child"
                    ? "dzieckiem"
                    : "malzonkiem"}
                  , lub dodaj nowa:
                </p>
                <div className="flex gap-2">
                  {persons
                    ?.filter((p) => p.id !== selectedPerson.id)
                    .map((p) => (
                      <button
                        key={p.id}
                        onClick={() => handleLink(p.id)}
                        className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-blue-50"
                      >
                        {p.names[0]?.given_name} {p.names[0]?.surname}
                      </button>
                    ))}
                  <button
                    onClick={() => setLinkMode(null)}
                    className="px-2 py-1 text-xs text-red-600 border border-red-200 rounded hover:bg-red-50"
                  >
                    Anuluj
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {searchingId && (
          <div className="max-w-2xl mt-6">
            <SearchPanel personId={searchingId} personName={searchName} />
          </div>
        )}

        {!selectedPerson && !searchingId && (
          <div className="flex items-center justify-center h-full text-gray-400">
            Wybierz osobe z listy po lewej
          </div>
        )}
      </div>
    </div>
  );
}
