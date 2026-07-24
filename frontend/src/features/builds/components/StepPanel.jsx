import { Button } from "@/components/ui/button";
import { t } from "../i18n";

export const StepPanel = ({ locale = "es", step, onExplain, onBuild }) => {
  if (!step) {
    return (
      <div className="border border-dashed border-border p-6 text-sm text-muted-foreground">
        {t(locale, "empty_history")}
      </div>
    );
  }

  const learnList = step.que_aprenderas || [];
  const localList = step.probar_en_local || [];
  const doneList = step.criterio_de_hecho || [];

  return (
    <div className="border border-border bg-card p-5 space-y-4" data-testid="step-panel">
      <div>
        <h2 className="font-heading text-xl font-black tracking-tight">{step.titulo}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{step.para_que}</p>
      </div>

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

      {localList.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground">{t(locale, "step_local")}</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
            {localList.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
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

      <div className="flex flex-wrap gap-2 pt-2">
        <Button variant="outline" onClick={() => onExplain?.(step)} data-testid="cta-explain">
          {t(locale, "cta_explain")}
        </Button>
        <Button onClick={() => onBuild?.(step)} data-testid="cta-build">
          {t(locale, "cta_build")}
        </Button>
      </div>
    </div>
  );
};
