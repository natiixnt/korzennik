import { useState, useEffect } from "react";
import type { Person } from "../../types/person";
import { useTriggerSearch, useSearchResults, useConfirmMatch, useRejectMatch } from "../../hooks/useSearch";
import { fetchRelationships } from "../../api/relationships";
import { useQuery } from "@tanstack/react-query";
import MatchCard from "../search/MatchCard";

interface Props {
  person: Person;
  allPersons: Person[];
}

type Tab = "info" | "search";

export default function PersonDetail({ person, allPersons }: Props) {
  const [tab, setTab] = useState<Tab>("info");

  // Reset to info tab when switching persons
  useEffect(() => {
    setTab("info");
  }, [person.id]);
  const primaryName = person.names.find((n) => n.is_primary) ?? person.names[0];
  const birth = person.events.find((e) => e.event_type === "birth");
  const death = person.events.find((e) => e.event_type === "death");
  const displayName = primaryName
    ? `${primaryName.given_name ?? ""} ${primaryName.surname ?? ""}`.trim()
    : "???";

  const { data: relationships } = useQuery({
    queryKey: ["relationships", person.id],
    queryFn: () => fetchRelationships(person.id),
  });

  const trigger = useTriggerSearch();
  const { data: results, isLoading: resultsLoading } = useSearchResults(person.id);
  const confirm = useConfirmMatch();
  const reject = useRejectMatch();

  // Resolve relationship names
  const parents = (relationships ?? [])
    .filter((r) => r.rel_type === "parent_child" && r.person2_id === person.id)
    .map((r) => allPersons.find((p) => p.id === r.person1_id))
    .filter(Boolean) as Person[];

  const children = (relationships ?? [])
    .filter((r) => r.rel_type === "parent_child" && r.person1_id === person.id)
    .map((r) => allPersons.find((p) => p.id === r.person2_id))
    .filter(Boolean) as Person[];

  const spouses = (relationships ?? [])
    .filter((r) => r.rel_type === "spouse")
    .map((r) => {
      const otherId = r.person1_id === person.id ? r.person2_id : r.person1_id;
      return allPersons.find((p) => p.id === otherId);
    })
    .filter(Boolean) as Person[];

  const formatPersonName = (p: Person) => {
    const n = p.names.find((n) => n.is_primary) ?? p.names[0];
    return n ? `${n.given_name ?? ""} ${n.surname ?? ""}`.trim() : "???";
  };

  return (
    <div className="space-y-4">
      {/* Person header */}
      <div className="flex items-start gap-3">
        <div
          className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold ${
            person.gender === "M"
              ? "bg-blue-500"
              : person.gender === "F"
              ? "bg-pink-500"
              : "bg-gray-400"
          }`}
        >
          {(primaryName?.given_name ?? "?")[0].toUpperCase()}
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-bold text-gray-900">{displayName}</h3>
          <p className="text-sm text-gray-500">
            {person.gender === "M" ? "Mezczyzna" : person.gender === "F" ? "Kobieta" : "Plec nieznana"}
            {" / "}
            <span className={`${
              person.origin === "user_entered" ? "text-green-600" :
              person.origin === "auto_discovered" ? "text-amber-600" : "text-blue-600"
            }`}>
              {person.origin === "user_entered" ? "Wprowadzony recznie" :
               person.origin === "auto_discovered" ? "Odkryty automatycznie" :
               person.origin === "confirmed_match" ? "Potwierdzony ze zrodla" : person.origin}
            </span>
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {([
          ["info", "Informacje"],
          ["search", "Wyszukiwanie"],
        ] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === key
                ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {label}
            {key === "search" && results && results.length > 0 && (
              <span className="ml-1.5 text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full">
                {results.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Info tab */}
      {tab === "info" && (
        <div className="space-y-4">
          {/* Life events */}
          <Section title="Daty i miejsca">
            {birth && (
              <InfoRow label="Urodzenie" value={[birth.date_text, birth.place_text].filter(Boolean).join(", ")} />
            )}
            {death && (
              <InfoRow label="Smierc" value={[death.date_text, death.place_text].filter(Boolean).join(", ")} />
            )}
            {person.events
              .filter((e) => e.event_type !== "birth" && e.event_type !== "death")
              .map((e) => (
                <InfoRow
                  key={e.id}
                  label={e.event_type === "immigration" ? "Imigracja" :
                         e.event_type === "emigration" ? "Emigracja" :
                         e.event_type === "residence" ? "Zamieszkanie" : e.event_type}
                  value={[e.date_text, e.place_text].filter(Boolean).join(", ")}
                />
              ))}
            {!birth && !death && person.events.length === 0 && (
              <p className="text-sm text-gray-400 italic">Brak danych</p>
            )}
          </Section>

          {/* Names */}
          {person.names.length > 1 && (
            <Section title="Inne imiona/nazwiska">
              {person.names.filter((n) => !n.is_primary).map((n) => (
                <InfoRow
                  key={n.id}
                  label={n.name_type === "married" ? "Po mezu" : n.name_type === "birth" ? "Rodowe" : n.name_type}
                  value={`${n.given_name ?? ""} ${n.surname ?? ""}`.trim()}
                />
              ))}
            </Section>
          )}

          {/* Family */}
          <Section title="Rodzina">
            {parents.length > 0 && (
              <div className="mb-2">
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Rodzice</span>
                {parents.map((p) => (
                  <PersonPill key={p.id} name={formatPersonName(p)} gender={p.gender} />
                ))}
              </div>
            )}
            {spouses.length > 0 && (
              <div className="mb-2">
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Malzonek</span>
                {spouses.map((p) => (
                  <PersonPill key={p.id} name={formatPersonName(p)} gender={p.gender} />
                ))}
              </div>
            )}
            {children.length > 0 && (
              <div className="mb-2">
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Dzieci</span>
                {children.map((p) => (
                  <PersonPill key={p.id} name={formatPersonName(p)} gender={p.gender} />
                ))}
              </div>
            )}
            {parents.length === 0 && spouses.length === 0 && children.length === 0 && (
              <p className="text-sm text-gray-400 italic">Brak polaczen rodzinnych</p>
            )}
          </Section>

          {/* Notes */}
          {person.notes && (
            <Section title="Notatki">
              <p className="text-sm text-gray-700">{person.notes}</p>
            </Section>
          )}
        </div>
      )}

      {/* Search tab */}
      {tab === "search" && (
        <div className="space-y-3">
          <button
            onClick={() => trigger.mutate({ personId: person.id })}
            disabled={trigger.isPending}
            className="w-full py-2 bg-[var(--color-primary)] text-white rounded-lg hover:bg-[var(--color-primary-light)] transition-colors disabled:opacity-50 text-sm font-medium"
          >
            {trigger.isPending ? "Szukanie..." : "Szukaj w 15 zrodlach"}
          </button>

          {resultsLoading && <p className="text-sm text-gray-400 text-center">Ladowanie wynikow...</p>}

          {results && results.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs text-gray-500">{results.length} wynikow</p>
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
            !resultsLoading && !trigger.isPending && (
              <p className="text-sm text-gray-400 text-center py-6">
                Kliknij "Szukaj" aby przeszukac bazy danych
              </p>
            )
          )}
        </div>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{title}</h4>
      <div className="bg-gray-50 rounded-lg p-3">{children}</div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div className="flex justify-between py-1 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-800 font-medium text-right">{value}</span>
    </div>
  );
}

function PersonPill({ name, gender }: { name: string; gender: string | null }) {
  return (
    <div className="flex items-center gap-2 py-1">
      <span
        className={`w-2 h-2 rounded-full ${
          gender === "M" ? "bg-blue-400" : gender === "F" ? "bg-pink-400" : "bg-gray-300"
        }`}
      />
      <span className="text-sm text-gray-700">{name}</span>
    </div>
  );
}
