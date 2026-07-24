import { useCallback, useEffect, useState } from "react";
import { ArrowClockwise, Coins, WarningCircle } from "@phosphor-icons/react";
import { fetchBudget } from "../api";
import { getApiError } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const fmtUsd = (v) => `$${Number(v ?? 0).toFixed(2)}`;

export const BudgetWidget = ({ refreshKey = 0, onBudgetChange }) => {
  const [state, setState] = useState({ status: "loading", data: null, error: "" });

  const load = useCallback(async () => {
    setState((s) => ({ ...s, status: "loading" }));
    try {
      const data = await fetchBudget();
      setState({ status: "success", data, error: "" });
      onBudgetChange?.(data);
    } catch (err) {
      setState({ status: "error", data: null, error: getApiError(err) });
    }
  }, [onBudgetChange]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  if (state.status === "loading") {
    return (
      <div className="border border-border bg-card p-5" data-testid="budget-widget-loading">
        <Skeleton className="h-4 w-40 rounded-none" />
        <Skeleton className="mt-4 h-2 w-full rounded-none" />
        <Skeleton className="mt-3 h-3 w-64 rounded-none" />
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div
        className="flex flex-col items-start gap-3 border-l-2 border-[#FF2A2A] bg-card p-5 sm:flex-row sm:items-center sm:justify-between"
        data-testid="budget-widget-error"
      >
        <div className="flex items-center gap-3">
          <WarningCircle size={22} className="shrink-0 text-[#FF2A2A]" />
          <div>
            <p className="text-sm font-medium">No se pudo cargar el presupuesto del día.</p>
            <p className="mt-0.5 font-mono text-xs text-muted-foreground">{state.error}</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={load} className="gap-2" data-testid="budget-widget-retry-button">
          <ArrowClockwise size={14} /> Reintentar
        </Button>
      </div>
    );
  }

  const { spent_usd, committed_usd, cap_usd, remaining_usd, per_build_cap_usd, date } = state.data;
  const totalCommitted = Number(spent_usd || 0) + Number(committed_usd || 0);
  const pct = cap_usd > 0 ? Math.min(100, (totalCommitted / cap_usd) * 100) : 0;
  const overBudget = totalCommitted >= cap_usd;

  return (
    <div className="border border-border bg-card p-5" data-testid="budget-widget-success">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Coins size={18} className="text-[#4D7CFF]" />
          <p className="font-heading text-lg font-black tracking-tighter">Presupuesto de hoy</p>
        </div>
        {date && <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{date}</p>}
      </div>

      <Progress
        value={pct}
        className={overBudget ? "mt-4 [&>div]:bg-[#FF2A2A]" : "mt-4"}
        aria-label={`Presupuesto usado: ${pct.toFixed(0)}% de ${fmtUsd(cap_usd)}`}
        data-testid="budget-progress-bar"
      />

      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 font-mono text-xs text-muted-foreground">
        <span data-testid="budget-spent">Gastado: {fmtUsd(spent_usd)}</span>
        <span data-testid="budget-committed">Comprometido: {fmtUsd(committed_usd)}</span>
        <span data-testid="budget-remaining">Disponible: {fmtUsd(remaining_usd)}</span>
        <span data-testid="budget-cap">Tope diario: {fmtUsd(cap_usd)}</span>
        <span data-testid="budget-per-build-cap">Tope por build: {fmtUsd(per_build_cap_usd)}</span>
      </div>
    </div>
  );
};
