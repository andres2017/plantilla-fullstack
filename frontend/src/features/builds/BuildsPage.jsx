import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { fetchBuilds, fetchBlueprint, fetchBlueprintProgress, estimateBuild } from "./api";
import { getApiError } from "@/lib/api";
import { BudgetWidget } from "./components/BudgetWidget";
import { BuildProgress } from "./components/BuildProgress";
import { BuildHistoryTable } from "./components/BuildHistoryTable";
import { BlueprintMap } from "./components/BlueprintMap";
import { StepPanel } from "./components/StepPanel";
import { EstimatePanel } from "./components/EstimatePanel";
import { ClaudeConnector } from "./components/ClaudeConnector";
import { ProjectBriefWizard } from "./components/ProjectBriefWizard";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { getLocale, setLocale, t } from "./i18n";

const ACTIVE_STATUSES = ["queued", "running"];

const PATHS = [
  {
    id: "ciclo_desarrollo",
    es: "Ciclo de desarrollo (7 fases)",
    en: "Development lifecycle (7 phases)",
    hint_es: "De la idea al mantenimiento. Ideal para todos.",
    hint_en: "From idea to maintenance. For everyone.",
  },
  {
    id: "full_stack",
    es: "App completa (plantilla técnica)",
    en: "Full-stack app (technical template)",
    hint_es: "Auth, datos, API, pantallas sobre el código real.",
    hint_en: "Auth, data, API, screens on the real codebase.",
  },
];

export default function BuildsPage() {
  const [locale, setLocaleState] = useState(getLocale);
  const [blueprintId, setBlueprintId] = useState("ciclo_desarrollo");
  const [activeBuildId, setActiveBuildId] = useState(null);
  const [checkingActive, setCheckingActive] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);
  const [blueprint, setBlueprint] = useState(null);
  const [progress, setProgress] = useState(null);
  const [selectedStepId, setSelectedStepId] = useState(null);
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("implement");
  const [estimating, setEstimating] = useState(false);
  const [estimate, setEstimate] = useState(null);
  const [budget, setBudget] = useState(null);
  const [llmStatus, setLlmStatus] = useState(null);
  const [preferredModel, setPreferredModel] = useState("sonnet");
  const [flow, setFlow] = useState(null);
  const [briefMeta, setBriefMeta] = useState(null);

  const switchLocale = (next) => {
    const v = setLocale(next);
    setLocaleState(v);
  };

  const bumpRefresh = useCallback(() => setRefreshTick((x) => x + 1), []);

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

  const loadBlueprint = useCallback(async () => {
    try {
      const [bp, prog] = await Promise.all([
        fetchBlueprint(blueprintId, locale),
        fetchBlueprintProgress(blueprintId, locale),
      ]);
      setBlueprint(bp);
      setProgress(prog);
      const firstId = bp?.pasos?.[0]?.id;
      setSelectedStepId((prev) => {
        if (prev && bp?.pasos?.some((p) => p.id === prev)) return prev;
        return firstId || null;
      });
    } catch (err) {
      toast.error(getApiError(err));
    }
  }, [locale, blueprintId]);

  useEffect(() => {
    loadBlueprint();
  }, [loadBlueprint, refreshTick]);

  const selectedStep = useMemo(() => {
    if (!blueprint?.pasos) return null;
    return blueprint.pasos.find((s) => s.id === selectedStepId) || null;
  }, [blueprint, selectedStepId]);

  const mapSteps = useMemo(() => {
    if (!blueprint?.pasos) return [];
    const stateById = Object.fromEntries((progress?.steps || []).map((s) => [s.id, s.state]));
    return blueprint.pasos.map((s) => ({
      ...s,
      state: stateById[s.id] || "pendiente",
    }));
  }, [blueprint, progress]);

  const resolveModel = () => preferredModel || selectedStep?.model_recomendado?.[mode] || "sonnet";

  const startBrief = (defaultMode) => {
    setMode(defaultMode);
    setEstimate(null);
    setPrompt("");
    setBriefMeta(null);
    setFlow("brief");
  };

  const handleBriefConfirm = (brief, composedPrompt) => {
    setBriefMeta(brief);
    setMode(brief.mode || mode);
    setPrompt(composedPrompt);
    setEstimate(null);
    setFlow("composer");
  };

  const handleEstimate = async () => {
    const trimmed = prompt.trim();
    if (trimmed.length < 15) {
      toast.error(locale === "en" ? "Write a longer prompt" : "Escribe un prompt mas largo");
      return;
    }
    setEstimating(true);
    try {
      const data = await estimateBuild({
        prompt: trimmed,
        template_type: briefMeta?.projectType || blueprintId,
        blueprint_step_id: selectedStepId || undefined,
        mode,
        locale,
        model: resolveModel(),
        agent: selectedStep?.agent_recomendado || undefined,
      });
      setEstimate(data);
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setEstimating(false);
    }
  };

  const handleBuildCreated = (build) => {
    setActiveBuildId(build.id);
    setEstimate(null);
    setFlow(null);
    bumpRefresh();
  };

  const handleBuildFinished = () => {
    setActiveBuildId(null);
    bumpRefresh();
  };

  const handleLlmStatus = (data) => {
    setLlmStatus(data);
    if (data?.preferred_model) setPreferredModel(data.preferred_model);
  };

  const switchPath = (id) => {
    setBlueprintId(id);
    setSelectedStepId(null);
    setFlow(null);
    setEstimate(null);
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6" data-testid="builds-page">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-heading text-4xl font-black tracking-tighter">{t(locale, "hero_title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t(locale, "hero_sub")}</p>
          {blueprint && (
            <p className="mt-2 text-xs text-muted-foreground">
              {blueprint.titulo} · v{blueprint.version}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant={locale === "es" ? "default" : "outline"} size="sm" onClick={() => switchLocale("es")}>
            {t(locale, "locale_es")}
          </Button>
          <Button variant={locale === "en" ? "default" : "outline"} size="sm" onClick={() => switchLocale("en")}>
            {t(locale, "locale_en")}
          </Button>
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2" data-testid="path-picker">
        {PATHS.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => switchPath(p.id)}
            className={`rounded border px-4 py-3 text-left transition ${
              blueprintId === p.id
                ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                : "border-border hover:border-primary/40"
            }`}
          >
            <p className="font-heading text-sm font-bold tracking-tight">
              {locale === "en" ? p.en : p.es}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {locale === "en" ? p.hint_en : p.hint_es}
            </p>
          </button>
        ))}
      </div>

      <ClaudeConnector locale={locale} onStatusChange={handleLlmStatus} />

      <BudgetWidget refreshKey={refreshTick} onBudgetChange={setBudget} />

      {(blueprint?.local_hint || blueprint?.publish_hint) && (
        <div className="grid gap-3 md:grid-cols-2">
          {blueprint.local_hint && (
            <div className="border border-border bg-card p-4 text-sm">
              <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground">{t(locale, "tab_local")}</p>
              <p className="mt-1 text-muted-foreground">{blueprint.local_hint}</p>
            </div>
          )}
          {blueprint.publish_hint && (
            <div className="border border-border bg-card p-4 text-sm">
              <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground">{t(locale, "tab_publish")}</p>
              <p className="mt-1 text-muted-foreground">{blueprint.publish_hint}</p>
            </div>
          )}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <BlueprintMap
          locale={locale}
          steps={mapSteps}
          progress={progress}
          selectedId={selectedStepId}
          onSelect={(step) => {
            setSelectedStepId(step.id);
            setFlow(null);
            setEstimate(null);
          }}
        />
        <div className="space-y-4">
          <StepPanel
            locale={locale}
            step={selectedStep}
            onAskClaude={() => startBrief("learn")}
            onBuild={() => startBrief("implement")}
          />

          {!checkingActive && !activeBuildId && flow === "brief" && (
            <ProjectBriefWizard
              locale={locale}
              defaultMode={mode}
              onConfirm={handleBriefConfirm}
              onCancel={() => setFlow(null)}
            />
          )}

          {!checkingActive && !activeBuildId && flow === "composer" && (
            <div className="border border-border bg-card p-5" data-testid="build-form">
              <div className="mb-2 flex flex-wrap gap-2 text-xs">
                <span className="rounded border px-2 py-0.5">
                  {t(locale, mode === "learn" ? "mode_learn" : "mode_implement")}
                </span>
                {selectedStepId && (
                  <span className="rounded border px-2 py-0.5 font-mono">{selectedStepId}</span>
                )}
                <span className="rounded border px-2 py-0.5 font-mono">{resolveModel()}</span>
                {llmStatus && !llmStatus.connected && (
                  <span className="rounded border border-amber-500/40 px-2 py-0.5 text-amber-400">stub</span>
                )}
              </div>
              <p className="mb-2 text-xs text-muted-foreground">
                {locale === "en"
                  ? "Prompt from your answers. Tokens only after you confirm the build."
                  : "Prompt con tus respuestas. Tokens solo al confirmar el build."}
              </p>
              <Label htmlFor="build-prompt" className="text-xs uppercase tracking-[0.2em]">
                {t(locale, "prompt_label")}
              </Label>
              <Textarea
                id="build-prompt"
                value={prompt}
                onChange={(e) => {
                  setPrompt(e.target.value);
                  setEstimate(null);
                }}
                className="mt-2 min-h-[140px] font-mono text-xs"
              />
              <div className="mt-4 flex flex-wrap gap-2">
                <Button disabled={estimating || prompt.trim().length < 15} onClick={handleEstimate}>
                  {estimating ? t(locale, "loading") : t(locale, "estimate")}
                </Button>
                <Button variant="outline" onClick={() => setFlow("brief")}>
                  {locale === "en" ? "Back to questions" : "Volver a preguntas"}
                </Button>
                <Button variant="ghost" onClick={() => setFlow(null)}>
                  {locale === "en" ? "Cancel" : "Cancelar"}
                </Button>
              </div>
              {estimate && (
                <div className="mt-5">
                  <EstimatePanel
                    estimate={estimate}
                    prompt={prompt.trim()}
                    budget={budget}
                    onBuildCreated={handleBuildCreated}
                    createPayload={{
                      template_type: briefMeta?.projectType || blueprintId,
                      blueprint_step_id: selectedStepId || undefined,
                      blueprint_version: blueprint?.version,
                      mode,
                      locale,
                      agent: selectedStep?.agent_recomendado,
                      model: resolveModel(),
                    }}
                  />
                </div>
              )}
            </div>
          )}

          {activeBuildId && (
            <BuildProgress buildId={activeBuildId} onFinished={handleBuildFinished} />
          )}
        </div>
      </div>

      <BuildHistoryTable refreshKey={refreshTick} locale={locale} />
    </div>
  );
}
