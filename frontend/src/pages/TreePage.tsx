import { useState, useCallback } from "react";
import { useTree } from "../hooks/useTree";
import FamilyTree from "../components/tree/FamilyTree";
import PersonForm from "../components/persons/PersonForm";
import SearchPanel from "../components/search/SearchPanel";
import DiscoveryPanel from "../components/search/DiscoveryPanel";
import EmptyCanvas from "../components/tree/EmptyCanvas";
import ContextMenu, { type ContextMenuItem } from "../components/tree/ContextMenu";
import { usePersons } from "../hooks/usePersons";
import { useDeletePerson } from "../hooks/usePersons";
import { createRelationship } from "../api/relationships";

type SidePanel = "add" | "search" | "discovery" | "add-parent" | "add-child" | "add-spouse" | null;

export default function TreePage() {
  const { data: treeData, isLoading } = useTree();
  const { data: persons } = usePersons();
  const deletePerson = useDeletePerson();
  const [selectedPerson, setSelectedPerson] = useState<string | null>(null);
  const [sidePanel, setSidePanel] = useState<SidePanel>(null);

  // Context menu state
  const [ctxMenu, setCtxMenu] = useState<{
    x: number;
    y: number;
    items: ContextMenuItem[];
  } | null>(null);

  // Linking state: after creating a relative, link them
  const [linkAfterCreate, setLinkAfterCreate] = useState<{
    targetPersonId: string;
    relType: "parent" | "child" | "spouse";
  } | null>(null);

  const selectedPersonData = persons?.find((p) => p.id === selectedPerson);
  const displayName = selectedPersonData?.names[0]
    ? `${selectedPersonData.names[0].given_name ?? ""} ${selectedPersonData.names[0].surname ?? ""}`.trim()
    : undefined;

  const closePanel = () => {
    setSidePanel(null);
    setLinkAfterCreate(null);
  };

  // Canvas right-click: add new person
  const handleCanvasRightClick = useCallback((x: number, y: number) => {
    setCtxMenu({
      x,
      y,
      items: [
        {
          label: "Dodaj osobe",
          icon: "+",
          onClick: () => {
            setLinkAfterCreate(null);
            setSidePanel("add");
          },
        },
        { label: "", onClick: () => {}, divider: true },
        {
          label: "Szukaj przodkow",
          icon: "?",
          onClick: () => setSidePanel("discovery"),
        },
      ],
    });
  }, []);

  // Node right-click: actions for that person
  const handleNodeRightClick = useCallback(
    (personId: string, x: number, y: number) => {
      const person = persons?.find((p) => p.id === personId);
      const name = person?.names[0]
        ? `${person.names[0].given_name ?? ""} ${person.names[0].surname ?? ""}`.trim()
        : "Osoba";

      setSelectedPerson(personId);

      setCtxMenu({
        x,
        y,
        items: [
          {
            label: `Szukaj dla: ${name}`,
            icon: "?",
            onClick: () => {
              setSelectedPerson(personId);
              setSidePanel("search");
            },
          },
          { label: "", onClick: () => {}, divider: true },
          {
            label: "Dodaj rodzica",
            icon: "^",
            onClick: () => {
              setLinkAfterCreate({ targetPersonId: personId, relType: "parent" });
              setSidePanel("add");
            },
          },
          {
            label: "Dodaj dziecko",
            icon: "v",
            onClick: () => {
              setLinkAfterCreate({ targetPersonId: personId, relType: "child" });
              setSidePanel("add");
            },
          },
          {
            label: "Dodaj malzonka",
            icon: "=",
            onClick: () => {
              setLinkAfterCreate({ targetPersonId: personId, relType: "spouse" });
              setSidePanel("add");
            },
          },
          { label: "", onClick: () => {}, divider: true },
          {
            label: "Usun",
            icon: "x",
            danger: true,
            onClick: () => {
              if (confirm(`Usunac ${name}?`)) {
                deletePerson.mutate(personId);
              }
            },
          },
        ],
      });
    },
    [persons, deletePerson]
  );

  // After creating a person, link them if needed
  const handlePersonCreated = async (newPersonId: string) => {
    if (linkAfterCreate) {
      const { targetPersonId, relType } = linkAfterCreate;
      try {
        if (relType === "parent") {
          await createRelationship({
            person1_id: newPersonId,
            person2_id: targetPersonId,
            rel_type: "parent_child",
          });
        } else if (relType === "child") {
          await createRelationship({
            person1_id: targetPersonId,
            person2_id: newPersonId,
            rel_type: "parent_child",
          });
        } else if (relType === "spouse") {
          await createRelationship({
            person1_id: targetPersonId,
            person2_id: newPersonId,
            rel_type: "spouse",
          });
        }
      } catch (e) {
        console.error("Failed to create relationship:", e);
      }
      setLinkAfterCreate(null);
    }
    setSidePanel(null);
  };

  const handleNodeClick = useCallback((id: string) => {
    setSelectedPerson(id);
    setSidePanel("search");
  }, []);

  const isEmpty = !treeData || treeData.length === 0;

  // Panel title
  const panelTitle = (() => {
    if (sidePanel === "discovery") return "Odkrywanie przodkow";
    if (sidePanel === "search") return "Wyszukiwanie";
    if (sidePanel === "add" && linkAfterCreate) {
      const role = linkAfterCreate.relType;
      return role === "parent" ? "Dodaj rodzica" : role === "child" ? "Dodaj dziecko" : "Dodaj malzonka";
    }
    return "Nowa osoba";
  })();

  return (
    <div className="h-full flex overflow-hidden">
      {/* Main canvas area */}
      <div className="flex-1 relative">
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-gray-300 border-t-[var(--color-primary)] rounded-full animate-spin" />
              Ladowanie drzewa...
            </div>
          </div>
        ) : isEmpty ? (
          <EmptyCanvas onAdd={() => setSidePanel("add")} />
        ) : (
          <FamilyTree
            treeData={treeData ?? []}
            onNodeClick={handleNodeClick}
            onNodeRightClick={handleNodeRightClick}
            onCanvasRightClick={handleCanvasRightClick}
          />
        )}

        {/* Bottom toolbar - only when tree has nodes */}
        {!isEmpty && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-white/90 backdrop-blur-sm rounded-xl shadow-lg border border-gray-200 px-2 py-1.5">
            <ToolbarButton
              label="Szukaj przodkow"
              active={sidePanel === "discovery"}
              onClick={() => setSidePanel(sidePanel === "discovery" ? null : "discovery")}
              primary
            />
            <div className="w-px h-6 bg-gray-200" />
            <ToolbarButton
              label="+ Dodaj osobe"
              active={sidePanel === "add" && !linkAfterCreate}
              onClick={() => {
                setLinkAfterCreate(null);
                setSidePanel(sidePanel === "add" ? null : "add");
              }}
            />
            <div className="w-px h-6 bg-gray-200" />
            <span className="text-xs text-gray-400 px-2">
              {treeData?.length ?? 0} osob
            </span>
          </div>
        )}
      </div>

      {/* Side panel */}
      {sidePanel && (
        <div className="w-[420px] border-l border-gray-200 bg-white flex flex-col shadow-xl">
          {/* Panel header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <h2 className="text-base font-semibold text-[var(--color-primary)]">
              {panelTitle}
            </h2>
            <button
              onClick={closePanel}
              className="w-7 h-7 flex items-center justify-center rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            >
              x
            </button>
          </div>

          {/* Panel content */}
          <div className="flex-1 overflow-y-auto p-4">
            {(sidePanel === "add" || sidePanel === "add-parent" || sidePanel === "add-child" || sidePanel === "add-spouse") && (
              <PersonForm onCreated={handlePersonCreated} />
            )}

            {sidePanel === "search" && selectedPerson && (
              <SearchPanel
                personId={selectedPerson}
                personName={displayName}
              />
            )}

            {sidePanel === "discovery" && <DiscoveryPanel />}
          </div>
        </div>
      )}

      {/* Context menu */}
      {ctxMenu && (
        <ContextMenu
          x={ctxMenu.x}
          y={ctxMenu.y}
          items={ctxMenu.items}
          onClose={() => setCtxMenu(null)}
        />
      )}
    </div>
  );
}

function ToolbarButton({
  label,
  active,
  onClick,
  primary,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
  primary?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-sm rounded-lg transition-colors font-medium ${
        active
          ? "bg-[var(--color-primary)] text-white"
          : primary
          ? "bg-[var(--color-primary)]/10 text-[var(--color-primary)] hover:bg-[var(--color-primary)]/20"
          : "text-gray-600 hover:bg-gray-100"
      }`}
    >
      {label}
    </button>
  );
}
