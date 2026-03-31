import { useState } from "react";
import { useCreatePerson } from "../../hooks/usePersons";
import type { PersonCreate } from "../../types/person";

interface Props {
  onCreated?: (id: string) => void;
  parentId?: string;
  parentRole?: "father" | "mother" | "child" | "spouse";
}

export default function PersonForm({ onCreated, parentId, parentRole }: Props) {
  const [givenName, setGivenName] = useState("");
  const [surname, setSurname] = useState("");
  const [gender, setGender] = useState<string>("");
  const [birthYear, setBirthYear] = useState("");
  const [birthPlace, setBirthPlace] = useState("");
  const [deathYear, setDeathYear] = useState("");
  const [deathPlace, setDeathPlace] = useState("");

  const create = useCreatePerson();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const data: PersonCreate = {
      gender: gender || null,
      names: [{ given_name: givenName || null, surname: surname || null, is_primary: true }],
      events: [],
    };

    if (birthYear || birthPlace) {
      data.events.push({
        event_type: "birth",
        date_year: birthYear ? parseInt(birthYear) : null,
        date_text: birthYear || null,
        place_text: birthPlace || null,
      });
    }

    if (deathYear || deathPlace) {
      data.events.push({
        event_type: "death",
        date_year: deathYear ? parseInt(deathYear) : null,
        date_text: deathYear || null,
        place_text: deathPlace || null,
      });
    }

    const person = await create.mutateAsync(data);
    onCreated?.(person.id);

    // Reset form
    setGivenName("");
    setSurname("");
    setGender("");
    setBirthYear("");
    setBirthPlace("");
    setDeathYear("");
    setDeathPlace("");
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-4 bg-white rounded-lg shadow">
      <h3 className="text-lg font-semibold text-[var(--color-primary)]">
        {parentRole
          ? `Dodaj ${parentRole === "father" ? "ojca" : parentRole === "mother" ? "matke" : parentRole === "child" ? "dziecko" : "malzonka"}`
          : "Dodaj osobe"}
      </h3>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Imie</label>
          <input
            type="text"
            value={givenName}
            onChange={(e) => setGivenName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent"
            placeholder="Jan"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nazwisko</label>
          <input
            type="text"
            value={surname}
            onChange={(e) => setSurname(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent"
            placeholder="Kowalski"
            required
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Plec</label>
        <select
          value={gender}
          onChange={(e) => setGender(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md"
        >
          <option value="">Nieznana</option>
          <option value="M">Mezczyzna</option>
          <option value="F">Kobieta</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Rok urodzenia</label>
          <input
            type="text"
            value={birthYear}
            onChange={(e) => setBirthYear(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="1885"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Miejsce urodzenia</label>
          <input
            type="text"
            value={birthPlace}
            onChange={(e) => setBirthPlace(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="Warszawa"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Rok smierci</label>
          <input
            type="text"
            value={deathYear}
            onChange={(e) => setDeathYear(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="1943"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Miejsce smierci</label>
          <input
            type="text"
            value={deathPlace}
            onChange={(e) => setDeathPlace(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder=""
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={create.isPending}
        className="w-full py-2 px-4 bg-[var(--color-primary)] text-white rounded-md hover:bg-[var(--color-primary-light)] transition-colors disabled:opacity-50"
      >
        {create.isPending ? "Dodawanie..." : "Dodaj do drzewa"}
      </button>
    </form>
  );
}
