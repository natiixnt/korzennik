export interface TreeNodeData {
  gender: string | null;
  first_name: string | null;
  last_name: string | null;
  birthday: string | null;
  deathday: string | null;
  birth_place: string | null;
  death_place: string | null;
  confidence: number;
  origin: string;
}

export interface TreeNodeRels {
  spouses: string[];
  parents: string[];
  children: string[];
}

export interface TreeNode {
  id: string;
  data: TreeNodeData;
  rels: TreeNodeRels;
}
