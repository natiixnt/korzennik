import { useCallback, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  ControlButton,
  MiniMap,
  type Edge,
  type Node,
  type NodeTypes,
  Position,
  ReactFlowProvider,
  useReactFlow,
  useNodesState,
  useEdgesState,
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
}

const NODE_WIDTH = 220;
const NODE_HEIGHT = 90;

function computeLayout(treeData: TreeNodeType[]) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 80, ranksep: 120, marginx: 40, marginy: 40 });

  for (const node of treeData) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }

  const edgeSet = new Set<string>();
  for (const node of treeData) {
    for (const parentId of node.rels.parents) {
      const key = `${parentId}->${node.id}`;
      if (!edgeSet.has(key)) {
        g.setEdge(parentId, node.id);
        edgeSet.add(key);
      }
    }
  }

  dagre.layout(g);

  const nodes: Node[] = treeData.map((tn) => {
    const pos = g.node(tn.id);
    return {
      id: tn.id,
      type: "person",
      position: {
        x: (pos?.x ?? 0) - NODE_WIDTH / 2,
        y: (pos?.y ?? 0) - NODE_HEIGHT / 2,
      },
      data: tn.data,
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      selectable: false,
    };
  });

  const edges: Edge[] = [];
  for (const node of treeData) {
    for (const parentId of node.rels.parents) {
      edges.push({
        id: `${parentId}-${node.id}`,
        source: parentId,
        target: node.id,
        type: "smoothstep",
        style: { stroke: "#94a3b8", strokeWidth: 2 },
      });
    }
    for (const spouseId of node.rels.spouses) {
      if (node.id < spouseId) {
        edges.push({
          id: `spouse-${node.id}-${spouseId}`,
          source: node.id,
          target: spouseId,
          type: "straight",
          style: {
            stroke: "#e11d48",
            strokeWidth: 1.5,
            strokeDasharray: "6,4",
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
}: Props) {
  const initialLayout = useMemo(() => computeLayout(treeData), [treeData]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialLayout.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialLayout.edges);
  const { fitView } = useReactFlow();

  // Sync when treeData changes (new person added etc.)
  const prevDataRef = useMemo(() => ({ len: treeData.length }), [treeData]);
  useMemo(() => {
    const layout = computeLayout(treeData);
    setNodes(layout.nodes);
    setEdges(layout.edges);
  }, [treeData, setNodes, setEdges]);

  // Auto-layout: reset all positions to dagre layout
  const handleAutoLayout = useCallback(() => {
    const layout = computeLayout(treeData);
    setNodes(layout.nodes);
    setEdges(layout.edges);
    // Slight delay to let React render new positions before fitting
    setTimeout(() => fitView({ padding: 0.3, duration: 300 }), 50);
  }, [treeData, setNodes, setEdges, fitView]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id);
    },
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
      onCanvasRightClick?.(
        (event as MouseEvent).clientX,
        (event as MouseEvent).clientY
      );
    },
    [onCanvasRightClick]
  );

  const handlePaneClick = useCallback(() => {
    onNodeClick?.("");
  }, [onNodeClick]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
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
      /* Touchpad: scroll = pan, pinch = zoom */
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
      <Controls
        showInteractive={false}
        className="!shadow-md !border-gray-200 !rounded-lg"
      >
        {/* Auto-layout button inside the controls panel */}
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
