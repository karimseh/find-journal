const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000/api";

export interface MatchResult {
  rank: number;
  title: string;
  issn: string | null;
  eissn: string | null;
  publisher: string;
  quartile: string | null;
  sjr: number | null;
  h_index: number | null;
  categories: string | null;
  areas: string | null;
  open_access: boolean;
  open_access_diamond: boolean;
  similarity_score: number;
}

export interface JournalEntry {
  title: string;
  issn: string | null;
  eissn: string | null;
  publisher: string;
  quartile: string | null;
  sjr: number | null;
  h_index: number | null;
  categories: string | null;
  areas: string | null;
  open_access: boolean;
  open_access_diamond: boolean;
}

export interface JournalsResponse {
  journals: JournalEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface Stats {
  total_journals: number;
  enriched_journals: number;
  quartile_distribution: Record<string, number>;
  top_publishers: Array<{ publisher: string; count: number }>;
}

export async function matchAbstract(
  abstract: string,
  options: { top_n?: number; quartiles?: string[]; min_sjr?: number } = {}
): Promise<MatchResult[]> {
  const res = await fetch(`${API_BASE}/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ abstract, ...options }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function searchJournals(
  q: string,
  limit = 20
): Promise<JournalEntry[]> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  const res = await fetch(`${API_BASE}/search?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getJournals(options: {
  quartile?: string;
  min_sjr?: number;
  page?: number;
  per_page?: number;
} = {}): Promise<JournalsResponse> {
  const params = new URLSearchParams();
  if (options.quartile) params.set("quartile", options.quartile);
  if (options.min_sjr != null) params.set("min_sjr", String(options.min_sjr));
  if (options.page) params.set("page", String(options.page));
  if (options.per_page) params.set("per_page", String(options.per_page));
  const res = await fetch(`${API_BASE}/journals?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getStats(): Promise<Stats> {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
