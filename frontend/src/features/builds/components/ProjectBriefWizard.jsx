import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

/**
 * Briefing previo al build — 0 tokens.
 * Arma un prompt claro solo cuando el usuario confirma.
 */
const PROJECT_TYPES = [
  { id: "web_landing", es: "Página web / Landing", en: "Website / Landing" },
  { id: "full_stack", es: "App completa (login + datos + API)", en: "Full-stack app (login + data + API)" },
  { id: "backend_api", es: "Solo API / backend", en: "API / backend only" },
  { id: "mobile_apk", es: "App móvil (Android)", en: "Mobile app (Android)" },
];

const AUDIENCES = [
  { id: "personal", es: "Uso personal / portafolio", en: "Personal / portfolio" },
  { id: "negocio", es: "Negocio / clientes", en: "Business / customers" },
  { id: "interno", es: "Equipo interno", en: "Internal team" },
  { id: "aprendiendo", es: "Solo estoy aprendiendo", en: "Just learning" },
];

const FEATURES = [
  { id: "login", es: "Login / cuentas", en: "Login / accounts" },
  { id: "crud", es: "Crear y listar datos", en: "Create & list data" },
  { id: "pagos", es: "Pagos", en: "Payments" },
  { id: "admin", es: "Panel admin", en: "Admin panel" },
  { id: "movil", es: "Versión móvil", en: "Mobile version" },
  { id: "publico", es: "Página pública (sin login)", en: "Public page (no login)" },
];

export function buildPromptFromBrief(brief, locale = "es") {
  const typeLabel =
    PROJECT_TYPES.find((t) => t.id === brief.projectType)?.[locale === "en" ? "en" : "es"] ||
    brief.projectType;
  const aud =
    AUDIENCES.find((a) => a.id === brief.audience)?.[locale === "en" ? "en" : "es"] ||
    brief.audience;
  const feats = (brief.features || [])
    .map((id) => FEATURES.find((f) => f.id === id)?.[locale === "en" ? "en" : "es"] || id)
    .join(", ");

  if (locale === "en") {
    return [
      `Project type: ${typeLabel}`,
      `Goal: ${brief.goal?.trim() || "(not specified)"}`,
      `Audience: ${aud}`,
      `Must-have features: ${feats || "(none selected)"}`,
      brief.extra?.trim() ? `Extra notes: ${brief.extra.trim()}` : null,
      "",
      brief.mode === "learn"
        ? "Respond with a clear step-by-step guide only (Markdown). Do not rewrite the whole repo. Explain order of work, folders to touch, local commands, and how to publish."
        : "Implement only what is needed for this brief on the existing template. Respect layers (router→service→repository) and the 4 UI states. Report files changed and how to test locally.",
    ]
      .filter(Boolean)
      .join("\n");
  }

  return [
    `Tipo de proyecto: ${typeLabel}`,
    `Objetivo: ${brief.goal?.trim() || "(sin especificar)"}`,
    `Para quién: ${aud}`,
    `Funciones que debe tener: ${feats || "(ninguna marcada)"}`,
    brief.extra?.trim() ? `Notas extra: ${brief.extra.trim()}` : null,
    "",
    brief.mode === "learn"
      ? "Responde SOLO con una guía paso a paso en Markdown. No reescribas todo el repo. Explica orden de trabajo, carpetas, comandos locales y cómo publicar."
      : "Implementa solo lo necesario para este brief sobre la plantilla existente. Respeta capas (router→service→repository) y los 4 estados de UI. Reporta archivos tocados y cómo probar en local.",
  ]
    .filter(Boolean)
    .join("\n");
}

export const ProjectBriefWizard = ({ locale = "es", defaultMode = "learn", onConfirm, onCancel }) => {
  const [step, setStep] = useState(0);
  const [projectType, setProjectType] = useState("web_landing");
  const [goal, setGoal] = useState("");
  const [audience, setAudience] = useState("aprendiendo");
  const [features, setFeatures] = useState(["publico"]);
  const [extra, setExtra] = useState("");
  const [mode, setMode] = useState(defaultMode);

  const toggleFeature = (id) => {
    setFeatures((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const canNext = useMemo(() => {
    if (step === 0) return Boolean(projectType);
    if (step === 1) return goal.trim().length >= 10;
    if (step === 2) return Boolean(audience);
    return true;
  }, [step, projectType, goal, audience]);

  const brief = { projectType, goal, audience, features, extra, mode };

  const title =
    locale === "en"
      ? ["What do you want to build?", "Describe the idea", "Who is it for?", "Confirm (no tokens yet)"]
      : ["¿Qué quieres construir?", "Describe la idea", "¿Para quién es?", "Confirmar (aún sin tokens)"];

  return (
    <div className="border border-border bg-card p-5 space-y-4" data-testid="project-brief-wizard">
      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary">
          {locale === "en" ? "Briefing · 0 tokens" : "Briefing · 0 tokens"}
        </p>
        <h3 className="font-heading text-lg font-black tracking-tight">{title[step]}</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          {locale === "en"
            ? "Answer a few questions so we know what you need before spending Claude tokens."
            : "Responde unas preguntas para saber qué necesitas antes de gastar tokens de Claude."}
        </p>
        <p className="mt-1 font-mono text-[11px] text-muted-foreground">
          {step + 1} / 4
        </p>
      </div>

      {step === 0 && (
        <div className="grid gap-2 sm:grid-cols-2">
          {PROJECT_TYPES.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setProjectType(t.id)}
              className={`rounded border px-3 py-3 text-left text-sm transition ${
                projectType === t.id
                  ? "border-primary bg-primary/10"
                  : "border-border hover:border-primary/40"
              }`}
            >
              {locale === "en" ? t.en : t.es}
            </button>
          ))}
        </div>
      )}

      {step === 1 && (
        <div className="space-y-3">
          <div>
            <Label className="text-xs uppercase tracking-[0.15em]">
              {locale === "en" ? "In one sentence, what should it do?" : "En una frase, ¿qué debe hacer?"}
            </Label>
            <Textarea
              className="mt-1 min-h-[100px]"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder={
                locale === "en"
                  ? "e.g. A landing page for my bakery with menu and WhatsApp button"
                  : "ej. Landing de mi panadería con menú y botón de WhatsApp"
              }
              data-testid="brief-goal"
            />
          </div>
          <div>
            <Label className="text-xs uppercase tracking-[0.15em]">
              {locale === "en" ? "Features (optional)" : "Funciones (opcional)"}
            </Label>
            <div className="mt-2 flex flex-wrap gap-2">
              {FEATURES.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => toggleFeature(f.id)}
                  className={`rounded border px-2.5 py-1 text-xs ${
                    features.includes(f.id)
                      ? "border-primary bg-primary/10"
                      : "border-border text-muted-foreground"
                  }`}
                >
                  {locale === "en" ? f.en : f.es}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="grid gap-2 sm:grid-cols-2">
          {AUDIENCES.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => setAudience(a.id)}
              className={`rounded border px-3 py-3 text-left text-sm ${
                audience === a.id ? "border-primary bg-primary/10" : "border-border"
              }`}
            >
              {locale === "en" ? a.en : a.es}
            </button>
          ))}
          <div className="sm:col-span-2">
            <Label className="text-xs uppercase tracking-[0.15em]">
              {locale === "en" ? "Anything else? (optional)" : "¿Algo más? (opcional)"}
            </Label>
            <Input
              className="mt-1"
              value={extra}
              onChange={(e) => setExtra(e.target.value)}
              placeholder={locale === "en" ? "Colors, deadline, constraints…" : "Colores, plazo, límites…"}
            />
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-3 text-sm">
          <div className="rounded border border-border bg-muted/20 p-3 space-y-1">
            <p>
              <span className="text-muted-foreground">{locale === "en" ? "Type:" : "Tipo:"}</span>{" "}
              {PROJECT_TYPES.find((t) => t.id === projectType)?.[locale === "en" ? "en" : "es"]}
            </p>
            <p>
              <span className="text-muted-foreground">{locale === "en" ? "Goal:" : "Objetivo:"}</span>{" "}
              {goal}
            </p>
            <p>
              <span className="text-muted-foreground">{locale === "en" ? "Audience:" : "Para quién:"}</span>{" "}
              {AUDIENCES.find((a) => a.id === audience)?.[locale === "en" ? "en" : "es"]}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground mb-2">
              {locale === "en" ? "What should Claude do?" : "¿Qué debe hacer Claude?"}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setMode("learn")}
                className={`rounded border px-3 py-2 text-xs ${
                  mode === "learn" ? "border-primary bg-primary/10" : "border-border"
                }`}
              >
                {locale === "en" ? "Guide only (cheaper)" : "Solo guía (más barato)"}
              </button>
              <button
                type="button"
                onClick={() => setMode("implement")}
                className={`rounded border px-3 py-2 text-xs ${
                  mode === "implement" ? "border-primary bg-primary/10" : "border-border"
                }`}
              >
                {locale === "en" ? "Build code on the template" : "Construir código en la plantilla"}
              </button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {locale === "en"
              ? "Next you’ll see the composed prompt and cost estimate. Tokens start only when you confirm the build."
              : "Luego verás el prompt armado y el estimado de costo. Los tokens empiezan solo al confirmar el build."}
          </p>
        </div>
      )}

      <div className="flex flex-wrap gap-2 pt-2">
        {step > 0 && (
          <Button type="button" variant="outline" onClick={() => setStep((s) => s - 1)}>
            {locale === "en" ? "Back" : "Atrás"}
          </Button>
        )}
        {step < 3 ? (
          <Button type="button" disabled={!canNext} onClick={() => setStep((s) => s + 1)}>
            {locale === "en" ? "Next" : "Siguiente"}
          </Button>
        ) : (
          <Button
            type="button"
            onClick={() => onConfirm?.(brief, buildPromptFromBrief(brief, locale))}
            data-testid="brief-confirm"
          >
            {locale === "en" ? "Continue to estimate" : "Continuar al estimado"}
          </Button>
        )}
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            {locale === "en" ? "Cancel" : "Cancelar"}
          </Button>
        )}
      </div>
    </div>
  );
};
