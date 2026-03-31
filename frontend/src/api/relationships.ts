import api from "./client";
import type { Relationship, RelationshipCreate } from "../types/relationship";

export async function createRelationship(
  rel: RelationshipCreate
): Promise<Relationship> {
  const { data } = await api.post<Relationship>("/relationships", rel);
  return data;
}

export async function fetchAllRelationships(): Promise<Relationship[]> {
  const { data } = await api.get<Relationship[]>("/relationships");
  return data;
}

export async function fetchRelationships(
  personId: string
): Promise<Relationship[]> {
  const { data } = await api.get<Relationship[]>(
    `/relationships/person/${personId}`
  );
  return data;
}

export async function deleteRelationship(relId: number): Promise<void> {
  await api.delete(`/relationships/${relId}`);
}
