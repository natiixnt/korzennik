import { useCallback, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type Node,
  type NodeTypes,
  Position,
  useReactFlow,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import dagre from "@dagrejs/dagre";
import type { TreeNode as TreeNodeType } from "../../types/tree";
import TreeNodeComponent from "./TreeNode";
import ContextMenu, { type ContextMenuItem } from "./ContextMenu";

const nodeTypes: NodeTypes = {
  person: TreeNodeComponent,
};

interface Props {
  treeData: TreeNodeType[];
  onNodeClick?: (personId: string) => void;
  onNodeRightClick?: (personId: string, x: number, y: number) => void;
  onCanvasRightClick?: (x: number, y: number) => void;
  onAddPerson?: () => void;
}

function buildLayout(treeData: TreeNodeType[]) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 80, ranksep: 120, marginx: 40, marginy: 40 });

  const nodeWidth = 220;
  const nodeHeight = 90;

  for (const node of treeData) {
    g.setNode(node.id, { width: nodeWidth, height: nodeHeight });
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
        x: (pos?.x ?? 0) - nodeWidth / 2,
        y: (pos?.y ?? 0) - nodeHeight / 2,
      },
      data: tn.data,
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
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
        animated: false,
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
  const { nodes, edges } = useMemo(() => buildLayout(treeData), [treeData]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick]
  );

  const handleNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: Node) => {
      event.preventDefault();
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

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={handleNodeClick}
      onNodeContextMenu={handleNodeContextMenu}
      onPaneContextMenu={handlePaneContextMenu}
      fitView
      fitViewOptions={{ padding: 0.3 }}
      minZoom={0.05}
      maxZoom={2.5}
      proOptions={{ hideAttribution: true }}
      nodesDraggable={true}
      panOnDrag={[0, 1]}
      selectionOnDrag={false}
    >
      <Background color="#d4d4d8" gap={20} size={1} />
      <Controls
        showInteractive={false}
        className="!shadow-md !border-gray-200 !rounded-lg"
      />
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
