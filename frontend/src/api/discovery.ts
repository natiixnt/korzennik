import api from "./client";

export interface DiscoveryProgress {
  run_id: string;
  status: string;
  total_persons: number;
  searched_persons: number;
  matches_found: number;
  auto_confirmed: number;
  cross_validated: number;
  new_persons_created: number;
  persons_enriched: number;
  current_person: string | null;
  current_depth: number;
  errors: string[];
  log: string[];
}

export interface DiscoveryStartResponse {
  run_id: string;
  status: string;
  message: string;
}

export async function startDiscovery(
  personIds?: string[],
  maxDepth?: number,
  autoConfirmThreshold?: number
): Promise<DiscoveryStartResponse> {
  const { data } = await api.post<DiscoveryStartResponse>("/discovery/start", {
    person_ids: personIds || null,
    max_depth: maxDepth ?? 10,
    auto_confirm_threshold: autoConfirmThreshold ?? 0.75,
  });
  return data;
}

export async function fetchDiscoveryProgress(
  runId: string
): Promise<DiscoveryProgress> {
  const { data } = await api.get<DiscoveryProgress>(
    `/discovery/${runId}/progress`
  );
  return data;
}

export async function stopDiscovery(runId: string): Promise<void> {
  await api.post(`/discovery/${runId}/stop`);
}

export async function fetchDiscoveryRuns(): Promise<DiscoveryProgress[]> {
  const { data } = await api.get<DiscoveryProgress[]>("/discovery/runs");
  return data;
}
