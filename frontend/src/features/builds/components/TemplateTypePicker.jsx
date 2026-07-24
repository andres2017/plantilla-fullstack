// Chips de tipo de entrega (que plantilla/alcance se va a editar). Controla
// template_type, que el backend usa para el addendum del system prompt del
// agente y para ajustar la heurística de estimate (ver docs/BUILDS.md).
import { TEMPLATE_TYPES } from "../constants";

export const TemplateTypePicker = ({ value, onChange, disabled = false }) => {
  const active = TEMPLATE_TYPES.find((t) => t.value === value) || TEMPLATE_TYPES[0];

  return (
    <div data-testid="template-type-picker">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Tipo de entrega</p>
      <div className="mt-2 flex flex-wrap gap-2" role="radiogroup" aria-label="Tipo de entrega">
        {TEMPLATE_TYPES.map((t) => {
          const selected = t.value === value;
          return (
            <button
              key={t.value}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={disabled}
              onClick={() => onChange(t.value)}
              data-testid={`template-type-chip-${t.value}`}
              className={[
                "border px-3 py-1.5 font-mono text-xs uppercase tracking-[0.1em] transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                selected
                  ? "border-[#4D7CFF] bg-[#4D7CFF]/10 text-[#4D7CFF]"
                  : "border-border bg-card text-muted-foreground hover:border-[#4D7CFF]/40 hover:text-foreground",
              ].join(" ")}
            >
              {t.label}
            </button>
          );
        })}
      </div>
      <p className="mt-2 text-xs text-muted-foreground" data-testid="template-type-help">
        {active.help}
      </p>
    </div>
  );
};
