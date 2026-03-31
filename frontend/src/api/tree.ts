import api from "./client";
import type { TreeNode } from "../types/tree";

export async function fetchTree(): Promise<TreeNode[]> {
  const { data } = await api.get<TreeNode[]>("/tree");
  return data;
}
