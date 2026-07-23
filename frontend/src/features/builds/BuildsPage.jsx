// Dashboard admin-only de la "fabrica Cyberandres" (MISION 14, ver
// docs/DECISIONS.md, entrada 2026-07-23). Orquesta 5 piezas: BudgetWidget
// (cabecera), BuildForm -> EstimatePanel (disparo), QueueProgressCard
// (progreso en vivo via SSE) y BuildHistoryTable (listado paginado). La ruta
// misma ya esta gateada por AdminRoute (features/auth/AdminRoute.jsx); el
// backend es la barrera real (403 sin excepcion).
//
// Estado global: NO se usa Context/Zustand aqui a proposito. Todo el estado
// (build activo, cursores de refresh) es local a esta pagina y se pasa hacia
// abajo por props — un solo consumidor (esta ruta), sin necesidad de
// compartir estado entre features distintas. Cada componente hijo maneja su
// propio ciclo de fetch/loading/error (mismo patron que ItemsPage.jsx).
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { fetchBuilds } from "./api";
import { getApiError } from "@/lib/api";
import { BudgetWidget } from "./components/BudgetWidget";
import { BuildForm } from "./components/BuildForm";
import { QueueProgressCard } from "./components/QueueProgressCard";
import { BuildHistoryTable } from "./components/BuildHistoryTable";

const ACTIVE_STATUSES = ["queued", "running"];

export default function BuildsPage() {
  const [activeBuildId, setActiveBuildId] = useState(null);
  const [checkingActive, setCheckingActive] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);

  // Al montar (o al refrescar la pestaña), revisa si ya hay un build
  // queued/running para reengancharse al SSE en vez de perder el progreso.
  useEffect(() => {
    let cancelled = false;
    fetchBuilds({ page: 1, limit: 5 })
      .then((data) => {
        if (cancelled) return;
        const inProgress = data.items.find((b) => ACTIVE_STATUSES.includes(b.status));
        if (inProgress) setActiveBuildId(inProgress.id);
      })
      .catch((err) => {
        if (!cancelled) toast.error(getApiError(err));
      })
      .finally(() => {
        if (!cancelled) setCheckingActive(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const bumpRefresh = useCallback(() => setRefreshTick((t) => t + 1), []);

  const handleBuildCreated = useCallback(
    (build) => {
      setActiveBuildId(build.id);
      bumpRefresh();
    },
    [bumpRefresh]
  );

  const handleBuildFinished = useCallback(() => {
    setActiveBuildId(null);
    bumpRefresh();
  }, [bumpRefresh]);

  return (
    <div className="mx-auto max-w-5xl space-y-6" data-testid="builds-page">
      <div>
        <h1 className="font-heading text-4xl font-black tracking-tighter">Fábrica Cyberandres</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Edita una copia de la plantilla con un prompt en español, ejecutado por el Claude Agent SDK.
        </p>
      </div>

      <BudgetWidget refreshKey={refreshTick} />

      {!checkingActive && !activeBuildId && <BuildForm onBuildCreated={handleBuildCreated} />}

      {activeBuildId && <QueueProgressCard buildId={activeBuildId} onFinished={handleBuildFinished} />}

      <BuildHistoryTable refreshKey={refreshTick} />
    </div>
  );
}
