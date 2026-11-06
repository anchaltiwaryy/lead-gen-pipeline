"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  type LeadFilters,
  type LeadSummary,
  type Stats,
} from "@/lib/api";
import FunnelBar from "@/components/FunnelBar";
import FilterBar from "@/components/FilterBar";
import LeadBoard from "@/components/LeadBoard";
import LeadDrawer from "@/components/LeadDrawer";
import ConsoleDrawer from "@/components/ConsoleDrawer";
import { TerminalSquare, Radar } from "lucide-react";

const DEBOUNCE_MS = 350;

export default function Home() {
  const [leads, setLeads] = useState<LeadSummary[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [sources, setSources] = useState<string[]>([]);
  const [filters, setFilters] = useState<LeadFilters>({});
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<number | null>(null);
  const [consoleOpen, setConsoleOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refreshStats = useCallback(async () => {
    try {
      const s = await api.stats();
      setStats(s);
      setSources(Object.keys(s.by_source));
    } catch {
      /* API offline */
    }
  }, []);

  const loadLeads = useCallback(async (f: LeadFilters) => {
    setLoading(true);
    try {
      const res = await api.listLeads(f);
      setLeads(res.items);
    } catch {
      setLeads([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshStats();
    loadLeads({});
  }, [refreshStats, loadLeads]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => loadLeads(filters), DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [filters, loadLeads]);

  return (
    <main className="mx-auto max-w-[1500px] space-y-4 p-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-accent/20 p-2">
            <Radar className="h-6 w-6 text-accent-hover" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">
              Lead Intelligence Engine
            </h1>
            <p className="text-xs text-slate-500">
              Autonomous Control Center · {stats?.total ?? "—"} leads tracked
            </p>
          </div>
        </div>
        <button onClick={() => setConsoleOpen(true)} className="btn-primary">
          <TerminalSquare className="h-4 w-4" /> Live Console
        </button>
      </header>

      <FunnelBar stats={stats} />

      <FilterBar filters={filters} onChange={setFilters} sources={sources} />

      <LeadBoard leads={leads} loading={loading} onSelect={(l) => setSelected(l.id)} />

      <LeadDrawer
        leadId={selected}
        onClose={() => setSelected(null)}
        onChanged={() => {
          refreshStats();
          loadLeads(filters);
        }}
      />

      <ConsoleDrawer open={consoleOpen} onClose={() => setConsoleOpen(false)} />
    </main>
  );
}