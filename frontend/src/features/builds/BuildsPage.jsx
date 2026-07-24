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
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { getLocale, setLocale, t } from "./i18n";

const ACTIVE_STATUSES = ["queued", "running"];
const BLUEPRINT_ID = "full_stack";

export default function BuildsPage() {
  const [locale, setLocaleState] = useState(getLocale);
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
        fetchBlueprint(BLUEPRINT_ID, locale),
        fetchBlueprintProgress(BLUEPRINT_ID, locale),
      ]);
      setBlueprint(bp);
      setProgress(prog);
      if (!selectedStepId && bp?.pasos?.length) {
        setSelectedStepId(bp.pasos[0].id);
      }
    } catch (err) {
      toast.error(getApiError(err));
    }
  }, [locale, selectedStepId]);

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

  const resolveModel = () =>
    preferredModel ||
    selectedStep?.model_recomendado?.[mode] ||
    "sonnet";

  const applyStep = (step, nextMode) => {
    setSelectedStepId(step.id);
    setMode(nextMode);
    const text =
      nextMode === "learn"
        ? step.prompt_learn || step.prompt_implement || ""
        : step.prompt_implement || step.prompt_learn || "";
    setPrompt(text);
    setEstimate(null);
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
        template_type: BLUEPRINT_ID,
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
          <Button
            variant={locale === "es" ? "default" : "outline"}
            size="sm"
            onClick={() => switchLocale("es")}
            data-testid="locale-es"
          >
            {t(locale, "locale_es")}
          </Button>
          <Button
            variant={locale === "en" ? "default" : "outline"}
            size="sm"
            onClick={() => switchLocale("en")}
            data-testid="locale-en"
          >
            {t(locale, "locale_en")}
          </Button>
        </div>
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
          onSelect={(step) => setSelectedStepId(step.id)}
        />
        <div className="space-y-4">
          <StepPanel
            locale={locale}
            step={selectedStep}
            onExplain={(step) => applyStep(step, "learn")}
            onBuild={(step) => applyStep(step, "implement")}
          />

          {!checkingActive && !activeBuildId && (
            <div className="border border-border bg-card p-5" data-testid="build-form">
              <div className="mb-2 flex flex-wrap gap-2 text-xs">
                <span className="rounded border px-2 py-0.5">{t(locale, mode === "learn" ? "mode_learn" : "mode_implement")}</span>
                {selectedStepId && <span className="rounded border px-2 py-0.5 font-mono">{selectedStepId}</span>}
                <span className="rounded border px-2 py-0.5 font-mono">{resolveModel()}</span>
                {llmStatus && !llmStatus.connected && (
                  <span className="rounded border border-amber-500/40 px-2 py-0.5 text-amber-400">
                    stub
                  </span>
                )}
              </div>
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
                className="mt-2 min-h-[120px]"
                data-testid="build-prompt-textarea"
              />
              <Button className="mt-4" disabled={estimating || prompt.trim().length < 15} onClick={handleEstimate}>
                {estimating ? t(locale, "loading") : t(locale, "estimate")}
              </Button>
              {estimate && (
                <div className="mt-5">
                  <EstimatePanel
                    estimate={estimate}
                    prompt={prompt.trim()}
                    budget={budget}
                    onBuildCreated={handleBuildCreated}
                    createPayload={{
                      template_type: BLUEPRINT_ID,
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
