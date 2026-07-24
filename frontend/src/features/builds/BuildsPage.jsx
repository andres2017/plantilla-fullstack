// Dashboard admin-only de la "fabrica Cyberandres" (MISION 14, ver
// docs/DECISIONS.md). Hero + selector de tipo de entrega + agente/modelo +
// composer de prompt -> estimate -> confirmar -> progreso en vivo (SSE) ->
// historial. La ruta misma ya esta gateada por AdminRoute
// (features/auth/AdminRoute.jsx); el backend es la barrera real (403 sin
// excepcion).
//
// Estado global: NO se usa Context/Zustand aqui a proposito. Todo el estado
// del formulario (tipo, agente, modelo, prompt, estimado) vive en esta
// pagina y se pasa hacia abajo por props — un solo consumidor (esta ruta).
// BudgetWidget/BuildHistoryTable mantienen su propio ciclo fetch/loading/error
// (mismo patron que ItemsPage.jsx).
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { fetchBuilds, estimateBuild } from "./api";
import { getApiError } from "@/lib/api";
import { BudgetWidget } from "./components/BudgetWidget";
import { TemplateTypePicker } from "./components/TemplateTypePicker";
import { AgentModelPicker } from "./components/AgentModelPicker";
import { PromptComposer, MIN_PROMPT_LENGTH } from "./components/PromptComposer";
import { EstimatePanel } from "./components/EstimatePanel";
import { BuildProgress } from "./components/BuildProgress";
import { BuildHistoryTable } from "./components/BuildHistoryTable";

const ACTIVE_STATUSES = ["queued", "running"];

export default function BuildsPage() {
  const [activeBuildId, setActiveBuildId] = useState(null);
  const [checkingActive, setCheckingActive] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);
  const [budget, setBudget] = useState(null);

  const [templateType, setTemplateType] = useState("full_stack");
  const [agent, setAgent] = useState("implementer");
  const [model, setModel] = useState("sonnet");
  const [prompt, setPrompt] = useState("");
  const [estimating, setEstimating] = useState(false);
  const [estimate, setEstimate] = useState(null);

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

  const trimmed = prompt.trim();
  const canEstimate = trimmed.length >= MIN_PROMPT_LENGTH && !estimating;

  const handlePromptChange = (value) => {
    setPrompt(value);
    if (estimate) setEstimate(null);
  };

  const handleTemplateTypeChange = (value) => {
    setTemplateType(value);
    if (estimate) setEstimate(null);
  };

  const handleEstimate = async () => {
    setEstimating(true);
    try {
      const data = await estimateBuild(trimmed, { templateType, model });
      setEstimate(data);
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setEstimating(false);
    }
  };

  const handleBuildCreated = useCallback(
    (build) => {
      setEstimate(null);
      setPrompt("");
      setActiveBuildId(build.id);
      bumpRefresh();
    },
    [bumpRefresh]
  );

  const handleBuildFinished = useCallback(() => {
    setActiveBuildId(null);
    bumpRefresh();
  }, [bumpRefresh]);

  const showForm = !checkingActive && !activeBuildId;

  return (
    <div className="mx-auto max-w-5xl space-y-6" data-testid="builds-page">
      <div className="text-center sm:text-left">
        <h1 className="font-heading text-4xl font-black tracking-tighter sm:text-5xl">¿Qué vas a construir hoy?</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Edita una copia de la plantilla con IA, en español — elegí el tipo de entrega, el agente y el modelo, y
          confirmá con el costo ya sobre la mesa.
        </p>
      </div>

      <BudgetWidget refreshKey={refreshTick} onBudgetChange={setBudget} />

      {showForm && (
        <div className="space-y-4">
          <div className="border border-border bg-card p-5">
            <TemplateTypePicker value={templateType} onChange={handleTemplateTypeChange} disabled={estimating} />
            <div className="mt-5 border-t border-border pt-5">
              <AgentModelPicker
                agent={agent}
                model={model}
                onAgentChange={setAgent}
                onModelChange={setModel}
                templateType={templateType}
                promptLength={trimmed.length}
                disabled={estimating}
              />
            </div>
          </div>

          <PromptComposer
            templateType={templateType}
            value={prompt}
            onChange={handlePromptChange}
            estimating={estimating}
            canEstimate={canEstimate}
            onEstimate={handleEstimate}
          />

          {estimate && (
            <EstimatePanel
              estimate={estimate}
              prompt={trimmed}
              budget={budget}
              templateType={templateType}
              agent={agent}
              model={model}
              onBuildCreated={handleBuildCreated}
            />
          )}
        </div>
      )}

      {activeBuildId && <BuildProgress buildId={activeBuildId} onFinished={handleBuildFinished} />}

      <BuildHistoryTable refreshKey={refreshTick} />
    </div>
  );
}
