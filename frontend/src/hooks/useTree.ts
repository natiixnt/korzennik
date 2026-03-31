import { useQuery } from "@tanstack/react-query";
import { fetchTree } from "../api/tree";

export function useTree() {
  return useQuery({
    queryKey: ["tree"],
    queryFn: fetchTree,
  });
}
