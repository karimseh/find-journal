import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { Analytics } from "@vercel/analytics/react";
import { Separator } from "@/components/ui/separator";
import MatchPage from "@/pages/MatchPage";
import BrowsePage from "@/pages/BrowsePage";

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-6">
          <NavLink to="/" className="font-semibold text-lg tracking-tight">
            FindJournal
          </NavLink>
          <Separator orientation="vertical" className="h-5" />
          <nav className="flex gap-4 text-sm">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                isActive
                  ? "text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground transition-colors"
              }
            >
              Match
            </NavLink>
            <NavLink
              to="/browse"
              className={({ isActive }) =>
                isActive
                  ? "text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground transition-colors"
              }
            >
              Browse
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-8 flex-1 w-full">
        {children}
      </main>
      <footer className="border-t py-4 text-center text-sm text-muted-foreground mt-auto">
        Created by{" "}
        <a
          href="https://karimdev.me"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-foreground transition-colors"
        >
          Karim Sehimi
        </a>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<MatchPage />} />
          <Route path="/browse" element={<BrowsePage />} />
        </Routes>
      </Layout>
      <Analytics />
    </BrowserRouter>
  );
}
