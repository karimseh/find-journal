import { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  getJournals,
  searchJournals,
  type JournalEntry,
  type JournalsResponse,
} from "@/services/api";

const QUARTILE_OPTIONS = ["Q1", "Q2", "Q3", "Q4"] as const;
const PER_PAGE = 30;

function quartileColor(q: string | null) {
  switch (q) {
    case "Q1": return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200";
    case "Q2": return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
    case "Q3": return "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200";
    case "Q4": return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
    default: return "bg-muted text-muted-foreground";
  }
}

export default function BrowsePage() {
  const [journals, setJournals] = useState<JournalEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedQuartiles, setSelectedQuartiles] = useState<string[]>([]);
  const [minSjr, setMinSjr] = useState("");

  const isSearchMode = searchQuery.trim().length > 0;

  const fetchJournals = useCallback(async () => {
    setLoading(true);
    try {
      if (isSearchMode) {
        const data = await searchJournals(searchQuery, 50);
        setJournals(data);
        setTotal(data.length);
      } else {
        const data: JournalsResponse = await getJournals({
          quartile: selectedQuartiles.length ? selectedQuartiles.join(",") : undefined,
          min_sjr: minSjr ? parseFloat(minSjr) : undefined,
          page,
          per_page: PER_PAGE,
        });
        setJournals(data.journals);
        setTotal(data.total);
      }
    } catch {
      // silently fail for browsing
    } finally {
      setLoading(false);
    }
  }, [isSearchMode, searchQuery, selectedQuartiles, minSjr, page]);

  useEffect(() => {
    fetchJournals();
  }, [fetchJournals]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [searchQuery, selectedQuartiles, minSjr]);

  function toggleQuartile(q: string) {
    setSelectedQuartiles((prev) =>
      prev.includes(q) ? prev.filter((x) => x !== q) : [...prev, q]
    );
  }

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Browse Journals</h1>
        <p className="text-muted-foreground mt-1">
          Explore the {total.toLocaleString()} DGRSDT Category A journals in the database.
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2 flex-1 min-w-[200px]">
              <Label htmlFor="search">Search by title</Label>
              <Input
                id="search"
                placeholder="e.g. blockchain, security..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Quartile</Label>
              <div className="flex gap-2">
                {QUARTILE_OPTIONS.map((q) => (
                  <Badge
                    key={q}
                    variant={selectedQuartiles.includes(q) ? "default" : "outline"}
                    className="cursor-pointer select-none"
                    onClick={() => toggleQuartile(q)}
                  >
                    {q}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="browse-sjr">Min SJR</Label>
              <Input
                id="browse-sjr"
                type="number"
                step="0.1"
                min="0"
                placeholder="0.0"
                value={minSjr}
                onChange={(e) => setMinSjr(e.target.value)}
                className="w-28"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-3">
        <h2 className="text-lg font-semibold">
          {loading ? "Loading..." : `${total.toLocaleString()} journals`}
        </h2>

        {journals.map((j, i) => (
          <Card key={`${j.issn}-${i}`}>
            <CardContent className="py-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <h3 className="font-medium">{j.title}</h3>
                  <p className="text-sm text-muted-foreground mt-1">{j.publisher}</p>
                  {j.areas && (
                    <p className="text-xs text-muted-foreground mt-1">{j.areas}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                  {j.quartile && (
                    <Badge variant="secondary" className={quartileColor(j.quartile)}>
                      {j.quartile}
                    </Badge>
                  )}
                  {j.open_access_diamond ? (
                    <Badge variant="secondary" className="bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-200">
                      Diamond OA
                    </Badge>
                  ) : j.open_access ? (
                    <Badge variant="secondary" className="bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200">
                      Gold OA
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                      Free
                    </Badge>
                  )}
                  <div className="text-right">
                    {j.sjr != null && (
                      <div className="text-sm tabular-nums">SJR {j.sjr.toFixed(3)}</div>
                    )}
                    {j.h_index != null && (
                      <div className="text-xs text-muted-foreground tabular-nums">
                        H-Index {j.h_index}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {!loading && journals.length === 0 && (
          <p className="text-center text-muted-foreground py-8">No journals found.</p>
        )}

        {!isSearchMode && totalPages > 1 && (
          <div className="flex items-center justify-between pt-4">
            <p className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
