import api from "./client";
import type { Person, PersonCreate } from "../types/person";

export async function fetchPersons(): Promise<Person[]> {
  const { data } = await api.get<Person[]>("/persons");
  return data;
}

export async function fetchPerson(id: string): Promise<Person> {
  const { data } = await api.get<Person>(`/persons/${id}`);
  return data;
}

export async function createPerson(person: PersonCreate): Promise<Person> {
  const { data } = await api.post<Person>("/persons", person);
  return data;
}

export async function deletePerson(id: string): Promise<void> {
  await api.delete(`/persons/${id}`);
}
