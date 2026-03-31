import { useState } from "react";
import { useTree } from "../hooks/useTree";
import FamilyTree from "../components/tree/FamilyTree";
import PersonForm from "../components/persons/PersonForm";
import SearchPanel from "../components/search/SearchPanel";
import DiscoveryPanel from "../components/search/DiscoveryPanel";
import { usePersons } from "../hooks/usePersons";

export default function TreePage() {
  const { data: treeData, isLoading } = useTree();
  const { data: persons } = usePersons();
  const [selectedPerson, setSelectedPerson] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showDiscovery, setShowDiscovery] = useState(false);

  const selectedPersonName = persons?.find((p) => p.id === selectedPerson);
  const displayName = selectedPersonName?.names[0]
    ? `${selectedPersonName.names[0].given_name ?? ""} ${selectedPersonName.names[0].surname ?? ""}`.trim()
    : undefined;

  const closeSidePanel = () => {
    setShowAddForm(false);
    setShowSearch(false);
    setShowDiscovery(false);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Top bar with discovery button */}
      <div className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between">
        <div className="text-sm text-gray-500">
          {treeData?.length ?? 0} osob w drzewie
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setShowDiscovery(!showDiscovery);
              setShowAddForm(false);
              setShowSearch(false);
            }}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
              showDiscovery
                ? "bg-[var(--color-primary)] text-white"
                : "bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-light)]"
            }`}
          >
            Szukaj przodkow
          </button>
          <button
            onClick={() => {
              setShowAddForm(!showAddForm);
              setShowSearch(false);
              setShowDiscovery(false);
            }}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium"
          >
            + Dodaj osobe
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Tree visualization */}
        <div className="flex-1 relative">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              Ladowanie drzewa...
            </div>
          ) : (
            <FamilyTree
              treeData={treeData ?? []}
              onNodeClick={(id) => {
                setSelectedPerson(id);
                setShowSearch(true);
                setShowAddForm(false);
                setShowDiscovery(false);
              }}
            />
          )}
        </div>

        {/* Side panel */}
        {(showAddForm || showSearch || showDiscovery) && (
          <div className="w-[480px] border-l border-gray-200 bg-white overflow-y-auto">
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-[var(--color-primary)]">
                  {showAddForm
                    ? "Nowa osoba"
                    : showDiscovery
                    ? "Odkrywanie przodkow"
                    : "Wyszukiwanie"}
                </h2>
                <button
                  onClick={closeSidePanel}
                  className="text-gray-400 hover:text-gray-600 text-lg"
                >
                  X
                </button>
              </div>

              {showAddForm && (
                <PersonForm onCreated={() => setShowAddForm(false)} />
              )}

              {showSearch && selectedPerson && (
                <SearchPanel
                  personId={selectedPerson}
                  personName={displayName}
                />
              )}

              {showDiscovery && <DiscoveryPanel />}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
