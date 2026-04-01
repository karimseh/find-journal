import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { matchAbstract, type MatchResult } from "@/services/api";

const QUARTILE_OPTIONS = ["Q1", "Q2", "Q3", "Q4"] as const;

function quartileColor(q: string | null) {
  switch (q) {
    case "Q1":
      return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200";
    case "Q2":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
    case "Q3":
      return "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200";
    case "Q4":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
    default:
      return "bg-muted text-muted-foreground";
  }
}

export default function MatchPage() {
  const [abstract, setAbstract] = useState("");
  const [results, setResults] = useState<MatchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedQuartiles, setSelectedQuartiles] = useState<string[]>([]);
  const [minSjr, setMinSjr] = useState("");
  const [topN, setTopN] = useState("15");

  function toggleQuartile(q: string) {
    setSelectedQuartiles((prev) =>
      prev.includes(q) ? prev.filter((x) => x !== q) : [...prev, q],
    );
  }

  async function handleMatch() {
    if (!abstract.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const desired = parseInt(topN) || 15;
      // Fetch a larger pool so client-side filtering has enough candidates
      const data = await matchAbstract(abstract, { top_n: 200 });

      let filtered = data;
      if (selectedQuartiles.length) {
        filtered = filtered.filter(
          (r) => r.quartile && selectedQuartiles.includes(r.quartile),
        );
      }
      if (minSjr) {
        const threshold = parseFloat(minSjr);
        filtered = filtered.filter((r) => r.sjr != null && r.sjr >= threshold);
      }

      // Slice to desired count and re-rank
      filtered = filtered.slice(0, desired);
      filtered.forEach((r, i) => (r.rank = i + 1));

      setResults(filtered);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Find a Journal
        </h1>
        <p className="text-muted-foreground mt-1">
          Paste your abstract and we'll match it to the most relevant DGRSDT
          Category A journals.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Your Abstract</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="Paste your research abstract here..."
            value={abstract}
            onChange={(e) => setAbstract(e.target.value)}
            rows={8}
            className="resize-y"
          />

          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label>Quartile filter</Label>
              <div className="flex gap-2">
                {QUARTILE_OPTIONS.map((q) => (
                  <Badge
                    key={q}
                    variant={
                      selectedQuartiles.includes(q) ? "default" : "outline"
                    }
                    className="cursor-pointer select-none"
                    onClick={() => toggleQuartile(q)}
                  >
                    {q}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="min-sjr">Min SJR</Label>
              <Input
                id="min-sjr"
                type="number"
                step="0.1"
                min="0"
                placeholder="e.g. 0.5"
                value={minSjr}
                onChange={(e) => setMinSjr(e.target.value)}
                className="w-28"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="top-n">Results</Label>
              <Input
                id="top-n"
                type="number"
                min="1"
                max="50"
                value={topN}
                onChange={(e) => setTopN(e.target.value)}
                className="w-20"
              />
            </div>

            <Button
              onClick={handleMatch}
              disabled={loading || !abstract.trim()}
            >
              {loading ? "Matching..." : "Match"}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-4">
            Note: Due to journal updates, the publication mode (Open Access
            status) may not always be accurate.
          </p>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6 text-destructive">{error}</CardContent>
        </Card>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">
            {results.length} matching journal{results.length !== 1 && "s"}
          </h2>
          {results.map((r) => (
            <Card key={`${r.rank}-${r.issn}`}>
              <CardContent className="py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm text-muted-foreground font-mono">
                        #{r.rank}
                      </span>
                      <h3 className="font-medium">{r.title}</h3>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {r.publisher}
                    </p>
                    {r.categories && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {r.categories}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                    {r.quartile && (
                      <Badge
                        variant="secondary"
                        className={quartileColor(r.quartile)}
                      >
                        {r.quartile}
                      </Badge>
                    )}
                    {r.open_access_diamond ? (
                      <Badge
                        variant="secondary"
                        className="bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-200"
                      >
                        Diamond OA
                      </Badge>
                    ) : r.open_access ? (
                      <Badge
                        variant="secondary"
                        className="bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200"
                      >
                        Gold OA
                      </Badge>
                    ) : (
                      <Badge
                        variant="secondary"
                        className="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                      >
                        Free
                      </Badge>
                    )}
                    <div className="text-right">
                      <div className="text-sm font-medium tabular-nums">
                        {(r.similarity_score * 100).toFixed(1)}%
                      </div>
                      {r.sjr != null && (
                        <div className="text-xs text-muted-foreground tabular-nums">
                          SJR {r.sjr.toFixed(3)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
