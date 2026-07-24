// Selects de agente y modelo. El modelo recomendado (segun tipo de entrega +
// largo del prompt, ver constants.js::recommendModel) se marca con una
// etiqueta "Recomendado" — es solo una sugerencia visual, no bloquea otras
// opciones ni se envia como flag al backend.
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { AGENTS, MODELS, recommendModel } from "../constants";

export const AgentModelPicker = ({
  agent,
  model,
  onAgentChange,
  onModelChange,
  templateType,
  promptLength = 0,
  disabled = false,
}) => {
  const recommended = recommendModel(templateType, promptLength);

  return (
    <div className="grid gap-4 sm:grid-cols-2" data-testid="agent-model-picker">
      <div>
        <Label htmlFor="agent-select" className="text-xs uppercase tracking-[0.2em]">
          Agente
        </Label>
        <Select value={agent} onValueChange={onAgentChange} disabled={disabled}>
          <SelectTrigger id="agent-select" className="mt-2 rounded-none" data-testid="agent-select-trigger">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="rounded-none">
            {AGENTS.map((a) => (
              <SelectItem key={a.value} value={a.value} data-testid={`agent-option-${a.value}`}>
                {a.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="mt-1.5 text-xs text-muted-foreground" data-testid="agent-help">
          {AGENTS.find((a) => a.value === agent)?.help}
        </p>
      </div>

      <div>
        <Label htmlFor="model-select" className="text-xs uppercase tracking-[0.2em]">
          Modelo
        </Label>
        <Select value={model} onValueChange={onModelChange} disabled={disabled}>
          <SelectTrigger id="model-select" className="mt-2 rounded-none" data-testid="model-select-trigger">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="rounded-none">
            {MODELS.map((m) => (
              <SelectItem key={m.value} value={m.value} data-testid={`model-option-${m.value}`}>
                {m.label}
                {m.value === recommended ? " · Recomendado" : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="mt-1.5 text-xs text-muted-foreground" data-testid="model-help">
          {MODELS.find((m) => m.value === model)?.help}
          {model !== recommended && (
            <span className="text-[#FFB300]">
              {" "}
              · Para este caso solemos recomendar{" "}
              {MODELS.find((m) => m.value === recommended)?.label.toLowerCase()}.
            </span>
          )}
        </p>
      </div>
    </div>
  );
};
