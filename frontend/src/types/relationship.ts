export interface Relationship {
  id: number;
  person1_id: string;
  person2_id: string;
  rel_type: string;
  confidence: number;
  source: string | null;
}

export interface RelationshipCreate {
  person1_id: string;
  person2_id: string;
  rel_type: string;
  confidence?: number;
  source?: string | null;
}
