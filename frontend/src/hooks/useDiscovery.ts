import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchDiscoveryProgress,
  startDiscovery,
  stopDiscovery,
  type DiscoveryProgress,
} from "../api/discovery";
import { useState } from "react";

export function useDiscovery() {
  const qc = useQueryClient();
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const start = useMutation({
    mutationFn: ({
      personIds,
      maxDepth,
      threshold,
    }: {
      personIds?: string[];
      maxDepth?: number;
      threshold?: number;
    }) => startDiscovery(personIds, maxDepth, threshold),
    onSuccess: (data) => {
      setActiveRunId(data.run_id);
    },
  });

  const stop = useMutation({
    mutationFn: (runId: string) => stopDiscovery(runId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["discovery-progress"] });
      qc.invalidateQueries({ queryKey: ["tree"] });
      qc.invalidateQueries({ queryKey: ["persons"] });
    },
  });

  const progress = useQuery({
    queryKey: ["discovery-progress", activeRunId],
    queryFn: () => fetchDiscoveryProgress(activeRunId!),
    enabled: !!activeRunId,
    refetchInterval: (query) => {
      const data = query.state.data as DiscoveryProgress | undefined;
      if (data?.status === "running") {
        return 1500;
      }
      // Refresh tree/persons when done
      if (data?.status === "completed" || data?.status === "stopped") {
        qc.invalidateQueries({ queryKey: ["tree"] });
        qc.invalidateQueries({ queryKey: ["persons"] });
      }
      return false;
    },
  });

  return { start, stop, progress, activeRunId, setActiveRunId };
}
