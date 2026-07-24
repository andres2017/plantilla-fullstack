import { useState } from "react";
import { Button } from "@/components/ui/button";
import { t } from "../i18n";

/**
 * Panel del asistente: guía local (0 tokens) + acciones claras.
 * - Ver guía / ya visible = contenido del blueprint
 * - Preguntar a Claude = opcional (tokens)
 * - Construir = IA escribe código (tokens)
 */
export const StepPanel = ({ locale = "es", step, onAskClaude, onBuild }) => {
  const [showGuide, setShowGuide] = useState(true);

  if (!step) {
    return (
      <div className="border border-dashed border-border p-6 text-sm text-muted-foreground">
        {locale === "en"
          ? "Pick a step on the path. The assistant guide costs no tokens."
          : "Elige un paso del camino. La guía del asistente no gasta tokens."}
      </div>
    );
  }

  const learnList = step.que_aprenderas || [];
  const localList = step.probar_en_local || [];
  const doneList = step.criterio_de_hecho || [];
  const guide = step.guia || [];
  const files = step.archivos_tipicos || [];
  const senior = step.mentalidad_senior || [];

  return (
    <div className="border border-border bg-card p-5 space-y-4" data-testid="step-panel">
      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-primary">
          {locale === "en" ? "Assistant · free guide" : "Asistente · guía gratis"}
        </p>
        <h2 className="font-heading text-xl font-black tracking-tight">{step.titulo}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{step.para_que}</p>
      </div>

      <div className="rounded border border-primary/20 bg-primary/5 px-3 py-2 text-xs text-muted-foreground">
        {locale === "en"
          ? "Read the guide below at no cost. Only “Build with Claude” or “Ask Claude” uses your API key."
          : "Lee la guía abajo sin costo. Solo “Construir con Claude” o “Preguntar a Claude” usa tu API key."}
      </div>

      <Button
        variant="outline"
        size="sm"
        onClick={() => setShowGuide((v) => !v)}
        data-testid="toggle-guide"
      >
        {showGuide
          ? locale === "en"
            ? "Hide guide"
            : "Ocultar guía"
          : locale === "en"
            ? "Show step-by-step guide"
            : "Ver guía paso a paso"}
      </Button>

      {showGuide && (
        <div className="space-y-4 border-t border-border pt-4" data-testid="assistant-guide">
          {guide.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                {locale === "en" ? "Step by step" : "Paso a paso"}
              </p>
              {guide.map((block, i) => (
                <div key={i} className="text-sm leading-relaxed text-foreground/90">
                  {typeof block === "string" ? (
                    <p>{block}</p>
                  ) : (
                    <>
                      {block.titulo && (
                        <p className="font-semibold text-foreground">{block.titulo}</p>
                      )}
                      {block.texto && <p className="mt-1 text-muted-foreground">{block.texto}</p>}
                      {Array.isArray(block.items) && (
                        <ul className="mt-1 list-disc space-y-1 pl-5 text-muted-foreground">
                          {block.items.map((it) => (
                            <li key={it}>{it}</li>
                          ))}
                        </ul>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {learnList.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground">{t(locale, "step_learn")}</p>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                {learnList.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {files.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                {locale === "en" ? "Where to look in the project" : "Dónde mirar en el proyecto"}
              </p>
              <ul className="mt-1 space-y-1 font-mono text-xs text-muted-foreground">
                {files.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>
          )}

          {localList.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground">{t(locale, "step_local")}</p>
              <ol className="mt-1 list-decimal space-y-1 pl-5 text-sm">
                {localList.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
            </div>
          )}

          {doneList.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground">{t(locale, "step_done_criteria")}</p>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                {doneList.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {senior.length > 0 && (
            <div className="rounded border border-border bg-muted/30 p-3">
              <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground">
                {locale === "en" ? "Senior mindset" : "Mentalidad senior"}
              </p>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                {senior.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {step.publicar_pista && (
            <p className="text-xs text-muted-foreground">
              <span className="font-semibold">{locale === "en" ? "Ship tip: " : "Al publicar: "}</span>
              {step.publicar_pista}
            </p>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2 border-t border-border pt-4">
        <Button variant="outline" onClick={() => onAskClaude?.(step)} data-testid="cta-ask-claude">
          {locale === "en" ? "Ask Claude (uses tokens)" : "Preguntar a Claude (gasta tokens)"}
        </Button>
        <Button onClick={() => onBuild?.(step)} data-testid="cta-build">
          {locale === "en" ? "Build this step with Claude" : "Construir este paso con Claude"}
        </Button>
      </div>
    </div>
  );
};
