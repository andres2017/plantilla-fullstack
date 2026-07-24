import { t } from "../i18n";

const STATE_STYLE = {
  hecho: "border-emerald-500/50 bg-emerald-500/10 text-emerald-400",
  aprendido: "border-sky-500/50 bg-sky-500/10 text-sky-400",
  en_curso: "border-amber-500/50 bg-amber-500/10 text-amber-400",
  pendiente: "border-border bg-card text-muted-foreground",
  bloqueado: "border-border/50 bg-muted/20 text-muted-foreground",
  fallido: "border-red-500/50 bg-red-500/10 text-red-400",
};

export const BlueprintMap = ({
  locale = "es",
  steps = [],
  progress,
  selectedId,
  onSelect,
}) => {
  const done = progress?.done ?? 0;
  const total = progress?.total ?? steps.length;

  return (
    <div className="border border-border bg-card p-4" data-testid="blueprint-map">
      <div className="flex items-center justify-between gap-2">
        <p className="font-heading text-sm font-bold tracking-tight">{t(locale, "map_title")}</p>
        <p className="font-mono text-xs text-muted-foreground">
          {t(locale, "map_progress", { done, total })}
        </p>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full bg-primary transition-all"
          style={{ width: total ? `${Math.round((done / total) * 100)}%` : "0%" }}
        />
      </div>
      <p className="mt-2 text-[11px] text-muted-foreground">
        {locale === "en"
          ? "Click any step to open the free guide."
          : "Haz clic en cualquier paso para abrir la guía gratis."}
      </p>
      <ul className="mt-3 space-y-2">
        {steps.map((step) => {
          const state = step.state || "pendiente";
          const selected = selectedId === step.id;
          return (
            <li key={step.id}>
              <button
                type="button"
                onClick={() => onSelect?.(step)}
                className={`w-full border px-3 py-2 text-left text-sm transition ${
                  STATE_STYLE[state] || STATE_STYLE.pendiente
                } ${selected ? "ring-2 ring-primary" : ""}`}
                data-testid={`blueprint-step-${step.id}`}
              >
                <span className="font-medium">{step.titulo || step.id}</span>
                <span className="ml-2 font-mono text-[10px] uppercase opacity-80">
                  {t(locale, `state_${state}`) || state}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
};
