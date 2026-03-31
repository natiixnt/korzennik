import { useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  ControlButton,
  MiniMap,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeTypes,
  type EdgeTypes,
  Position,
  ReactFlowProvider,
  useReactFlow,
  useNodesState,
  useEdgesState,
  BaseEdge,
  getSmoothStepPath,
  getStraightPath,
  EdgeLabelRenderer,
} from "reactflow";
import "reactflow/dist/style.css";
import dagre from "@dagrejs/dagre";
import type { TreeNode as TreeNodeType } from "../../types/tree";
import TreeNodeComponent from "./TreeNode";

const nodeTypes: NodeTypes = {
  person: TreeNodeComponent,
};

interface Props {
  treeData: TreeNodeType[];
  onNodeClick?: (personId: string) => void;
  onNodeRightClick?: (personId: string, x: number, y: number) => void;
  onCanvasRightClick?: (x: number, y: number) => void;
  onEdgeDelete?: (edgeId: string, sourceId: string, targetId: string, relType: string) => void;
}

const NODE_WIDTH = 220;
const NODE_HEIGHT = 90;

// Custom edge with delete button on hover
function DeletableEdge({
  id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style, data,
}: EdgeProps) {
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  });

  return (
    <>
      <BaseEdge id={id} path={path} style={style} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: "all",
          }}
          className="group"
        >
          <button
            className="w-5 h-5 rounded-full bg-white border border-gray-300 text-gray-400 text-[10px] leading-none flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:border-red-300 hover:text-red-500 transition-all shadow-sm"
            onClick={(e) => {
              e.stopPropagation();
              const handler = (data as any)?._onDelete;
              if (handler) handler();
            }}
            title="Usun polaczenie"
          >
            x
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

function DeletableSpouseEdge({
  id, sourceX, sourceY, targetX, targetY, style, data,
}: EdgeProps) {
  const [path, labelX, labelY] = getStraightPath({
    sourceX, sourceY, targetX, targetY,
  });

  return (
    <>
      <BaseEdge id={id} path={path} style={style} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: "all",
          }}
          className="group"
        >
          <button
            className="w-5 h-5 rounded-full bg-white border border-gray-300 text-gray-400 text-[10px] leading-none flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:border-red-300 hover:text-red-500 transition-all shadow-sm"
            onClick={(e) => {
              e.stopPropagation();
              const handler = (data as any)?._onDelete;
              if (handler) handler();
            }}
            title="Usun polaczenie"
          >
            x
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

const edgeTypes: EdgeTypes = {
  deletableStep: DeletableEdge,
  deletableSpouse: DeletableSpouseEdge,
};

function computeLayout(
  treeData: TreeNodeType[],
  onEdgeDelete?: (edgeId: string, sourceId: string, targetId: string, relType: string) => void,
) {
  const nodeMap = new Map(treeData.map((n) => [n.id, n]));

  // Spouse pairs
  const spousePairs: [string, string][] = [];
  const spouseSeen = new Set<string>();
  for (const node of treeData) {
    for (const spouseId of node.rels.spouses) {
      const key = [node.id, spouseId].sort().join("--");
      if (!spouseSeen.has(key) && nodeMap.has(spouseId)) {
        spousePairs.push([node.id, spouseId]);
        spouseSeen.add(key);
      }
    }
  }

  // Merge spouse pairs: secondary -> primary
  const spouseOf = new Map<string, string>();
  for (const [a, b] of spousePairs) {
    const aConns = (nodeMap.get(a)?.rels.children.length ?? 0) + (nodeMap.get(a)?.rels.parents.length ?? 0);
    const bConns = (nodeMap.get(b)?.rels.children.length ?? 0) + (nodeMap.get(b)?.rels.parents.length ?? 0);
    if (aConns >= bConns) {
      spouseOf.set(b, a);
    } else {
      spouseOf.set(a, b);
    }
  }

  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 120, marginx: 40, marginy: 40 });

  for (const node of treeData) {
    if (spouseOf.has(node.id)) continue;
    const hasSpouse = [...spouseOf.values()].includes(node.id);
    const width = hasSpouse ? NODE_WIDTH * 2 + 40 : NODE_WIDTH;
    g.setNode(node.id, { width, height: NODE_HEIGHT });
  }

  const edgeSet = new Set<string>();
  for (const node of treeData) {
    for (const parentId of node.rels.parents) {
      const effectiveParent = spouseOf.get(parentId) ?? parentId;
      const effectiveChild = spouseOf.has(node.id) ? undefined : node.id;
      if (!effectiveChild) continue;
      const key = `${effectiveParent}->${effectiveChild}`;
      if (!edgeSet.has(key)) {
        g.setEdge(effectiveParent, effectiveChild);
        edgeSet.add(key);
      }
    }
  }

  dagre.layout(g);

  const positions = new Map<string, { x: number; y: number }>();
  for (const node of treeData) {
    if (spouseOf.has(node.id)) continue;
    const pos = g.node(node.id);
    if (!pos) continue;
    const hasSpouse = [...spouseOf.entries()].find(([_, primary]) => primary === node.id);
    if (hasSpouse) {
      const [secondaryId] = hasSpouse;
      const gap = 20;
      positions.set(node.id, { x: pos.x - (NODE_WIDTH + gap) / 2, y: pos.y });
      positions.set(secondaryId, { x: pos.x + (NODE_WIDTH + gap) / 2, y: pos.y });
    } else {
      positions.set(node.id, { x: pos.x, y: pos.y });
    }
  }

  const nodes: Node[] = treeData.map((tn) => {
    const p = positions.get(tn.id) ?? { x: 0, y: 0 };
    return {
      id: tn.id,
      type: "person",
      position: { x: p.x - NODE_WIDTH / 2, y: p.y - NODE_HEIGHT / 2 },
      data: tn.data,
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      selectable: false,
    };
  });

  const edges: Edge[] = [];
  for (const node of treeData) {
    for (const parentId of node.rels.parents) {
      const edgeId = `pc-${parentId}-${node.id}`;
      edges.push({
        id: edgeId,
        source: parentId,
        target: node.id,
        type: "deletableStep",
        style: { stroke: "#94a3b8", strokeWidth: 2 },
        data: {
          _onDelete: onEdgeDelete
            ? () => onEdgeDelete(edgeId, parentId, node.id, "parent_child")
            : undefined,
        },
      });
    }
    for (const spouseId of node.rels.spouses) {
      if (node.id < spouseId) {
        const edgeId = `sp-${node.id}-${spouseId}`;
        edges.push({
          id: edgeId,
          source: node.id,
          target: spouseId,
          type: "deletableSpouse",
          style: { stroke: "#e11d48", strokeWidth: 1.5, strokeDasharray: "6,4" },
          data: {
            _onDelete: onEdgeDelete
              ? () => onEdgeDelete(edgeId, node.id, spouseId, "spouse")
              : undefined,
          },
        });
      }
    }
  }

  return { nodes, edges };
}

function FamilyTreeInner({
  treeData,
  onNodeClick,
  onNodeRightClick,
  onCanvasRightClick,
  onEdgeDelete,
}: Props) {
  const initialLayout = useMemo(() => computeLayout(treeData, onEdgeDelete), [treeData, onEdgeDelete]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialLayout.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialLayout.edges);
  const { fitView } = useReactFlow();

  useMemo(() => {
    const layout = computeLayout(treeData, onEdgeDelete);
    setNodes(layout.nodes);
    setEdges(layout.edges);
  }, [treeData, onEdgeDelete, setNodes, setEdges]);

  const handleAutoLayout = useCallback(() => {
    const layout = computeLayout(treeData, onEdgeDelete);
    setNodes(layout.nodes);
    setEdges(layout.edges);
    setTimeout(() => fitView({ padding: 0.3, duration: 300 }), 50);
  }, [treeData, onEdgeDelete, setNodes, setEdges, fitView]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => { onNodeClick?.(node.id); },
    [onNodeClick]
  );

  const handleNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: Node) => {
      event.preventDefault();
      event.stopPropagation();
      onNodeRightClick?.(node.id, event.clientX, event.clientY);
    },
    [onNodeRightClick]
  );

  const handlePaneContextMenu = useCallback(
    (event: React.MouseEvent | MouseEvent) => {
      event.preventDefault();
      onCanvasRightClick?.((event as MouseEvent).clientX, (event as MouseEvent).clientY);
    },
    [onCanvasRightClick]
  );

  const handlePaneClick = useCallback(() => { onNodeClick?.(""); }, [onNodeClick]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={handleNodeClick}
      onNodeContextMenu={handleNodeContextMenu}
      onPaneContextMenu={handlePaneContextMenu}
      onPaneClick={handlePaneClick}
      fitView
      fitViewOptions={{ padding: 0.3 }}
      minZoom={0.05}
      maxZoom={2.5}
      proOptions={{ hideAttribution: true }}
      nodesDraggable={true}
      panOnScroll={true}
      zoomOnScroll={false}
      panOnDrag={true}
      selectionOnDrag={false}
      nodesConnectable={false}
      elementsSelectable={false}
      zoomOnPinch={true}
      zoomOnDoubleClick={false}
    >
      <Background color="#d4d4d8" gap={20} size={1} />
      <Controls showInteractive={false} className="!shadow-md !border-gray-200 !rounded-lg">
        <ControlButton onClick={handleAutoLayout} title="Wyrownaj uklad">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="1" y="1" width="5" height="5" rx="1" />
            <rect x="10" y="1" width="5" height="5" rx="1" />
            <rect x="5.5" y="10" width="5" height="5" rx="1" />
            <line x1="3.5" y1="6" x2="3.5" y2="8" />
            <line x1="12.5" y1="6" x2="12.5" y2="8" />
            <line x1="3.5" y1="8" x2="12.5" y2="8" />
            <line x1="8" y1="8" x2="8" y2="10" />
          </svg>
        </ControlButton>
      </Controls>
      <MiniMap
        nodeColor={(node) => {
          const d = node.data as any;
          if (d?.gender === "M") return "#60a5fa";
          if (d?.gender === "F") return "#f472b6";
          return "#d1d5db";
        }}
        maskColor="rgba(0,0,0,0.08)"
        className="!shadow-md !border-gray-200 !rounded-lg"
      />
    </ReactFlow>
  );
}

export default function FamilyTree(props: Props) {
  return (
    <ReactFlowProvider>
      <FamilyTreeInner {...props} />
    </ReactFlowProvider>
  );
}
