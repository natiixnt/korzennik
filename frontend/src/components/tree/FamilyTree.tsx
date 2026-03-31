import { useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
  type NodeTypes,
  Position,
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
}

function buildLayout(treeData: TreeNodeType[]) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 100 });

  const nodeWidth = 220;
  const nodeHeight = 100;

  // Add nodes
  for (const node of treeData) {
    g.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  }

  // Add edges (parent -> child)
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
      position: { x: (pos?.x ?? 0) - nodeWidth / 2, y: (pos?.y ?? 0) - nodeHeight / 2 },
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
      });
    }
    // Spouse connections (dashed)
    for (const spouseId of node.rels.spouses) {
      // Only add one direction to avoid duplicates
      if (node.id < spouseId) {
        edges.push({
          id: `spouse-${node.id}-${spouseId}`,
          source: node.id,
          target: spouseId,
          type: "straight",
          style: { stroke: "#e11d48", strokeWidth: 2, strokeDasharray: "5,5" },
        });
      }
    }
  }

  return { nodes, edges };
}

export default function FamilyTree({ treeData, onNodeClick }: Props) {
  const { nodes, edges } = useMemo(() => buildLayout(treeData), [treeData]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick]
  );

  if (treeData.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <div className="text-center">
          <p className="text-xl mb-2">Drzewo jest puste</p>
          <p className="text-sm">Dodaj pierwsza osobe aby rozpoczac</p>
        </div>
      </div>
    );
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={handleNodeClick}
      fitView
      minZoom={0.1}
      maxZoom={2}
    >
      <Background color="#d4d4d8" gap={20} />
      <Controls />
    </ReactFlow>
  );
}
