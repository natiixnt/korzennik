export interface SourceMatch {
  id: number;
  person_id: string;
  source_name: string;
  source_record_id: string;
  source_url: string | null;
  given_name: string | null;
  surname: string | null;
  birth_date: string | null;
  birth_place: string | null;
  death_date: string | null;
  death_place: string | null;
  father_name: string | null;
  mother_name: string | null;
  confidence_score: number;
  confidence_breakdown: Record<string, number> | null;
  status: string;
}

export interface TaskStatus {
  id: number;
  source_name: string;
  status: string;
  result_count: number;
  error_message: string | null;
}
