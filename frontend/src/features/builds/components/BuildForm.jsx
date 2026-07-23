// Textarea del prompt + boton explicito "Calcular costo estimado" (NO se
// dispara /builds/estimate en cada tecla — cada calculo es una decision
// deliberada porque el tamano del prompt define el costo). Al estimar,
// renderiza EstimatePanel debajo. Si el admin edita el prompt despues de
// tener un estimado, el estimado queda invalidado (evita confirmar un build
// contra un costo que ya no corresponde al texto actual).
import { useState } from "react";
import { toast } from "sonner";
import { Calculator } from "@phosphor-icons/react";
import { estimateBuild } from "../api";
import { getApiError } from "@/lib/api";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { EstimatePanel } from "./EstimatePanel";

const MIN_PROMPT_LENGTH = 15;

export const BuildForm = ({ onBuildCreated }) => {
  const [prompt, setPrompt] = useState("");
  const [estimating, setEstimating] = useState(false);
  const [estimate, setEstimate] = useState(null);

  const trimmed = prompt.trim();
  const tooShort = trimmed.length > 0 && trimmed.length < MIN_PROMPT_LENGTH;
  const canEstimate = trimmed.length >= MIN_PROMPT_LENGTH && !estimating;

  const handlePromptChange = (e) => {
    setPrompt(e.target.value);
    if (estimate) setEstimate(null);
  };

  const handleEstimate = async () => {
    setEstimating(true);
    try {
      const data = await estimateBuild(trimmed);
      setEstimate(data);
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setEstimating(false);
    }
  };

  const handleBuildCreated = (build) => {
    setEstimate(null);
    setPrompt("");
    onBuildCreated(build);
  };

  return (
    <div className="border border-border bg-card p-5" data-testid="build-form">
      <Label htmlFor="build-prompt" className="text-xs uppercase tracking-[0.2em]">
        Prompt para la fábrica
      </Label>
      <Textarea
        id="build-prompt"
        value={prompt}
        onChange={handlePromptChange}
        disabled={estimating}
        placeholder="Ej: Agrega un módulo de facturación con exportación a PDF y filtro por rango de fechas..."
        className="mt-2 min-h-[120px]"
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
          {prompt.length} caracteres
        </span>
      </div>

      <Button className="mt-4 gap-2" disabled={!canEstimate} onClick={handleEstimate} data-testid="estimate-button">
        <Calculator size={16} weight="bold" /> {estimating ? "Calculando..." : "Calcular costo estimado"}
      </Button>

      {estimate && (
        <div className="mt-5">
          <EstimatePanel estimate={estimate} prompt={trimmed} onBuildCreated={handleBuildCreated} />
        </div>
      )}
    </div>
  );
};
