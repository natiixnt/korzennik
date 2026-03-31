import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  confirmMatch,
  fetchSearchResults,
  fetchSearchStatus,
  rejectMatch,
  triggerSearch,
} from "../api/search";

export function useSearchResults(personId: string | null) {
  return useQuery({
    queryKey: ["search-results", personId],
    queryFn: () => fetchSearchResults(personId!),
    enabled: !!personId,
  });
}

export function useSearchStatus(personId: string | null) {
  return useQuery({
    queryKey: ["search-status", personId],
    queryFn: () => fetchSearchStatus(personId!),
    enabled: !!personId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.some((t) => t.status === "queued" || t.status === "running")) {
        return 2000;
      }
      return false;
    },
  });
}

export function useTriggerSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      personId,
      sources,
    }: {
      personId: string;
      sources?: string[];
    }) => triggerSearch(personId, sources),
    onSuccess: (_, { personId }) => {
      qc.invalidateQueries({ queryKey: ["search-status", personId] });
      qc.invalidateQueries({ queryKey: ["search-results", personId] });
    },
  });
}

export function useConfirmMatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (matchId: number) => confirmMatch(matchId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["search-results"] });
      qc.invalidateQueries({ queryKey: ["persons"] });
      qc.invalidateQueries({ queryKey: ["tree"] });
    },
  });
}

export function useRejectMatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (matchId: number) => rejectMatch(matchId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["search-results"] });
    },
  });
}
