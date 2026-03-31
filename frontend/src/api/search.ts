import api from "./client";
import type { SourceMatch, TaskStatus } from "../types/search";

export async function triggerSearch(
  personId: string,
  sources?: string[]
): Promise<TaskStatus[]> {
  const { data } = await api.post<TaskStatus[]>(`/search/${personId}`, {
    sources,
  });
  return data;
}

export async function fetchSearchStatus(
  personId: string
): Promise<TaskStatus[]> {
  const { data } = await api.get<TaskStatus[]>(`/search/${personId}/status`);
  return data;
}

export async function fetchSearchResults(
  personId: string
): Promise<SourceMatch[]> {
  const { data } = await api.get<SourceMatch[]>(`/search/${personId}/results`);
  return data;
}

export async function confirmMatch(matchId: number): Promise<SourceMatch> {
  const { data } = await api.post<SourceMatch>(
    `/search/matches/${matchId}/confirm`
  );
  return data;
}

export async function rejectMatch(matchId: number): Promise<SourceMatch> {
  const { data } = await api.post<SourceMatch>(
    `/search/matches/${matchId}/reject`
  );
  return data;
}
