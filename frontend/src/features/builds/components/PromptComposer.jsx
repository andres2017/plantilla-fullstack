// Textarea grande del prompt + contador de caracteres + ejemplo sugerido
// segun el tipo de entrega + boton explicito "Calcular costo estimado" (NO
// se dispara /builds/estimate en cada tecla — cada calculo es una decision
// deliberada porque el tamano del prompt define el costo).
import { Calculator, Lightbulb } from "@phosphor-icons/react";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { EXAMPLE_PROMPTS } from "../constants";

const MIN_PROMPT_LENGTH = 15;

export { MIN_PROMPT_LENGTH };

export const PromptComposer = ({
  templateType,
  value,
  onChange,
  estimating,
  canEstimate,
  onEstimate,
}) => {
  const trimmed = value.trim();
  const tooShort = trimmed.length > 0 && trimmed.length < MIN_PROMPT_LENGTH;
  const example = EXAMPLE_PROMPTS[templateType];

  return (
    <div className="border border-border bg-card p-5" data-testid="prompt-composer">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Label htmlFor="build-prompt" className="text-xs uppercase tracking-[0.2em]">
          ¿Qué vas a construir hoy?
        </Label>
        {example && (
          <button
            type="button"
            onClick={() => onChange(example)}
            className="flex items-center gap-1.5 font-mono text-xs text-[#4D7CFF] hover:underline"
            data-testid="prompt-use-example"
          >
            <Lightbulb size={14} /> Usar un ejemplo
          </button>
        )}
      </div>

      <Textarea
        id="build-prompt"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={estimating}
        placeholder={example || "Describe en español qué querés que la fábrica construya o edite..."}
        className="mt-2 min-h-[140px]"
        aria-describedby="build-prompt-hint"
        aria-invalid={tooShort}
        data-testid="build-prompt-textarea"
      />
      <div id="build-prompt-hint" className="mt-1.5 flex flex-wrap items-center justify-between gap-2 font-mono text-xs">
        <span className={tooShort ? "text-[#FF2A2A]" : "text-muted-foreground"} data-testid="build-prompt-error">
          {tooShort
            ? `Escribe al menos ${MIN_PROMPT_LENGTH} caracteres para calcular un costo confiable.`
            : "Entre más detallado el prompt, más preciso el estimado."}
        </span>
        <span className="text-muted-foreground" data-testid="build-prompt-char-count">
          {value.length} caracteres
        </span>
      </div>

      <Button className="mt-4 gap-2" disabled={!canEstimate} onClick={onEstimate} data-testid="estimate-button">
        <Calculator size={16} weight="bold" /> {estimating ? "Calculando..." : "Calcular costo estimado"}
      </Button>
    </div>
  );
};
