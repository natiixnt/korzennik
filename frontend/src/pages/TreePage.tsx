import { useState, useCallback, useRef } from "react";
import { useTree } from "../hooks/useTree";
import FamilyTree from "../components/tree/FamilyTree";
import PersonForm from "../components/persons/PersonForm";
import PersonDetail from "../components/persons/PersonDetail";
import DiscoveryPanel from "../components/search/DiscoveryPanel";
import EmptyCanvas from "../components/tree/EmptyCanvas";
import ContextMenu, { type ContextMenuItem } from "../components/tree/ContextMenu";
import { usePersons, useDeletePerson } from "../hooks/usePersons";
import { createRelationship, fetchAllRelationships, deleteRelationship } from "../api/relationships";
import { useQuery, useQueryClient } from "@tanstack/react-query";

type SidePanel = "add" | "detail" | "discovery" | null;

export default function TreePage() {
  const qc = useQueryClient();
  const { data: treeData, isLoading } = useTree();
  const { data: persons } = usePersons();
  const { data: allRels } = useQuery({
    queryKey: ["all-relationships"],
    queryFn: fetchAllRelationships,
  });
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

  // Use ref so callbacks always see current value
  const selectedPersonRef = useRef(selectedPerson);
  selectedPersonRef.current = selectedPerson;

  const selectedPersonData = persons?.find((p) => p.id === selectedPerson);

  const closePanel = () => {
    setSidePanel(null);
    setSelectedPerson(null);
    setLinkAfterCreate(null);
  };

  const closeCtxMenu = useCallback(() => setCtxMenu(null), []);

  // Canvas right-click
  const handleCanvasRightClick = useCallback((x: number, y: number) => {
    setCtxMenu({
      x,
      y,
      items: [
        {
          label: "Dodaj nowa osobe",
          onClick: () => {
            setLinkAfterCreate(null);
            setSidePanel("add");
          },
        },
        { label: "", onClick: () => {}, divider: true },
        {
          label: "Szukaj przodkow automatycznie",
          onClick: () => setSidePanel("discovery"),
        },
      ],
    });
  }, []);

  // Node right-click - does NOT open side panel, only shows menu
  const handleNodeRightClick = useCallback(
    (personId: string, x: number, y: number) => {
      const person = persons?.find((p) => p.id === personId);
      const name = person?.names[0]
        ? `${person.names[0].given_name ?? ""} ${person.names[0].surname ?? ""}`.trim()
        : "Osoba";

      setCtxMenu({
        x,
        y,
        items: [
          {
            label: "Pokaz profil",
            onClick: () => {
              setSelectedPerson(personId);
              setSidePanel("detail");
            },
          },
          { label: "", onClick: () => {}, divider: true },
          {
            label: "Dodaj rodzica",
            onClick: () => {
              setLinkAfterCreate({ targetPersonId: personId, relType: "parent" });
              setSidePanel("add");
            },
          },
          {
            label: "Dodaj dziecko",
            onClick: () => {
              setLinkAfterCreate({ targetPersonId: personId, relType: "child" });
              setSidePanel("add");
            },
          },
          {
            label: "Dodaj malzonka/malzonke",
            onClick: () => {
              setLinkAfterCreate({ targetPersonId: personId, relType: "spouse" });
              setSidePanel("add");
            },
          },
          { label: "", onClick: () => {}, divider: true },
          {
            label: "Usun osobe",
            danger: true,
            onClick: () => {
              if (confirm(`Na pewno usunac ${name}?`)) {
                deletePerson.mutate(personId);
                if (selectedPersonRef.current === personId) {
                  setSidePanel(null);
                  setSelectedPerson(null);
                }
              }
            },
          },
        ],
      });
    },
    [persons, deletePerson]
  );

  // Edge delete: find the relationship by person IDs and delete it
  const handleEdgeDelete = useCallback(
    async (_edgeId: string, sourceId: string, targetId: string, relType: string) => {
      if (!allRels) return;

      // Find matching relationship
      const rel = allRels.find((r) => {
        if (relType === "parent_child") {
          return r.rel_type === "parent_child" && r.person1_id === sourceId && r.person2_id === targetId;
        }
        if (relType === "spouse") {
          return (
            r.rel_type === "spouse" &&
            ((r.person1_id === sourceId && r.person2_id === targetId) ||
             (r.person1_id === targetId && r.person2_id === sourceId))
          );
        }
        return false;
      });

      if (!rel) return;

      const label = relType === "spouse" ? "malzenstwo" : "relacje rodzic-dziecko";
      if (!confirm(`Usunac ${label}?`)) return;

      try {
        await deleteRelationship(rel.id);
        qc.invalidateQueries({ queryKey: ["tree"] });
        qc.invalidateQueries({ queryKey: ["all-relationships"] });
        qc.invalidateQueries({ queryKey: ["persons"] });
        qc.invalidateQueries({ queryKey: ["relationships"] });
      } catch (e) {
        console.error("Failed to delete relationship:", e);
      }
    },
    [allRels, qc]
  );

  // Left-click on node opens detail panel
  const handleNodeClick = useCallback((id: string) => {
    // Empty string = clicked on empty pane
    if (!id) {
      // Don't close panel on pane click, just deselect
      return;
    }
    setSelectedPerson(id);
    setSidePanel("detail");
  }, []);

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
    // After creating, show the new person's detail
    setSelectedPerson(newPersonId);
    setSidePanel("detail");
  };

  const isEmpty = !treeData || treeData.length === 0;

  const panelTitle = (() => {
    if (sidePanel === "discovery") return "Odkrywanie przodkow";
    if (sidePanel === "detail") {
      const n = selectedPersonData?.names[0];
      return n ? `${n.given_name ?? ""} ${n.surname ?? ""}`.trim() : "Profil";
    }
    if (sidePanel === "add" && linkAfterCreate) {
      const role = linkAfterCreate.relType;
      return role === "parent" ? "Dodaj rodzica" : role === "child" ? "Dodaj dziecko" : "Dodaj malzonka/malzonke";
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
            onEdgeDelete={handleEdgeDelete}
          />
        )}

        {/* Bottom toolbar */}
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
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 shrink-0">
            <h2 className="text-base font-semibold text-[var(--color-primary)] truncate pr-2">
              {panelTitle}
            </h2>
            <button
              onClick={closePanel}
              className="w-7 h-7 flex items-center justify-center rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors shrink-0"
            >
              x
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {sidePanel === "add" && (
              <PersonForm onCreated={handlePersonCreated} />
            )}

            {sidePanel === "detail" && selectedPersonData && (
              <PersonDetail
                person={selectedPersonData}
                allPersons={persons ?? []}
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
          onClose={closeCtxMenu}
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
