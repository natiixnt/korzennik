import { useState } from "react";
import { useCreatePerson } from "../../hooks/usePersons";
import type { PersonCreate } from "../../types/person";

interface Props {
  onCreated?: (id: string) => void;
}

export default function PersonForm({ onCreated }: Props) {
  const [givenName, setGivenName] = useState("");
  const [surname, setSurname] = useState("");
  const [gender, setGender] = useState<string>("");
  const [birthDate, setBirthDate] = useState("");
  const [birthPlace, setBirthPlace] = useState("");
  const [deathDate, setDeathDate] = useState("");
  const [deathPlace, setDeathPlace] = useState("");

  const create = useCreatePerson();

  const extractYear = (dateStr: string): number | null => {
    if (!dateStr) return null;
    // Handle YYYY-MM-DD from date input
    const match = dateStr.match(/(\d{4})/);
    return match ? parseInt(match[1]) : null;
  };

  const formatDateText = (dateStr: string): string | null => {
    if (!dateStr) return null;
    // Input type="date" gives YYYY-MM-DD, keep as-is (our date parser handles it)
    return dateStr;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const data: PersonCreate = {
      gender: gender || null,
      names: [{ given_name: givenName || null, surname: surname || null, is_primary: true }],
      events: [],
    };

    if (birthDate || birthPlace) {
      data.events.push({
        event_type: "birth",
        date_year: extractYear(birthDate),
        date_text: formatDateText(birthDate),
        place_text: birthPlace || null,
      });
    }

    if (deathDate || deathPlace) {
      data.events.push({
        event_type: "death",
        date_year: extractYear(deathDate),
        date_text: formatDateText(deathDate),
        place_text: deathPlace || null,
      });
    }

    const person = await create.mutateAsync(data);
    onCreated?.(person.id);

    setGivenName("");
    setSurname("");
    setGender("");
    setBirthDate("");
    setBirthPlace("");
    setDeathDate("");
    setDeathPlace("");
  };

  const inputClass =
    "w-full px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent";

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Imie</label>
          <input
            type="text"
            value={givenName}
            onChange={(e) => setGivenName(e.target.value)}
            className={inputClass}
            placeholder="Jan"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Nazwisko</label>
          <input
            type="text"
            value={surname}
            onChange={(e) => setSurname(e.target.value)}
            className={inputClass}
            placeholder="Kowalski"
            required
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Plec</label>
        <select
          value={gender}
          onChange={(e) => setGender(e.target.value)}
          className={inputClass}
        >
          <option value="">Nieznana</option>
          <option value="M">Mezczyzna</option>
          <option value="F">Kobieta</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Data urodzenia</label>
          <input
            type="date"
            value={birthDate}
            onChange={(e) => setBirthDate(e.target.value)}
            className={inputClass}
          />
          <p className="text-[10px] text-gray-400 mt-0.5">Lub wpisz sam rok, np. 1885</p>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Miejsce urodzenia</label>
          <input
            type="text"
            value={birthPlace}
            onChange={(e) => setBirthPlace(e.target.value)}
            className={inputClass}
            placeholder="Warszawa"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Data smierci</label>
          <input
            type="date"
            value={deathDate}
            onChange={(e) => setDeathDate(e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Miejsce smierci</label>
          <input
            type="text"
            value={deathPlace}
            onChange={(e) => setDeathPlace(e.target.value)}
            className={inputClass}
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={create.isPending}
        className="w-full py-2 px-4 bg-[var(--color-primary)] text-white rounded-lg text-sm font-medium hover:bg-[var(--color-primary-light)] transition-colors disabled:opacity-50"
      >
        {create.isPending ? "Dodawanie..." : "Dodaj do drzewa"}
      </button>
    </form>
  );
}
