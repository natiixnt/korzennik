export interface PersonName {
  id: number;
  name_type: string;
  given_name: string | null;
  surname: string | null;
  prefix: string | null;
  suffix: string | null;
  is_primary: boolean;
}

export interface PersonEvent {
  id: number;
  event_type: string;
  date_text: string | null;
  date_year: number | null;
  place_text: string | null;
  place_normalized: string | null;
  description: string | null;
}

export interface Person {
  id: string;
  origin: string;
  gender: string | null;
  is_living: boolean;
  notes: string | null;
  names: PersonName[];
  events: PersonEvent[];
}

export interface PersonCreate {
  gender?: string | null;
  is_living?: boolean;
  notes?: string | null;
  names: {
    name_type?: string;
    given_name?: string | null;
    surname?: string | null;
    is_primary?: boolean;
  }[];
  events: {
    event_type: string;
    date_text?: string | null;
    date_year?: number | null;
    place_text?: string | null;
  }[];
}
