import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createPerson, deletePerson, fetchPersons } from "../api/persons";
import type { PersonCreate } from "../types/person";

export function usePersons() {
  return useQuery({
    queryKey: ["persons"],
    queryFn: fetchPersons,
  });
}

export function useCreatePerson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PersonCreate) => createPerson(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["persons"] }),
  });
}

export function useDeletePerson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deletePerson(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["persons"] }),
  });
}
