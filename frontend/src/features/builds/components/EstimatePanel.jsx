// Panel que aparece tras estimar (POST /builds/estimate). Explica el costo,
// tokens y size_bucket; si within_budget es false, explica exactamente por
// que (tope por build vs presupuesto diario restante) y deshabilita el boton
// de confirmar. Cada click de "Confirmar y ejecutar" cuesta dinero real, asi
// que pasa por un AlertDialog de confirmacion explicita — el backend vuelve a
// validar el presupuesto server-side de todas formas (este disable es UX).
import { useState } from "react";
import { toast } from "sonner";
import { RocketLaunch, WarningCircle } from "@phosphor-icons/react";
import { createBuild } from "../api";
import { getApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const fmtUsd = (v) => `$${Number(v ?? 0).toFixed(4)}`;

const BUCKET_LABELS = { pequeño: "Pequeño", pequeno: "Pequeño", mediano: "Mediano", grande: "Grande" };

export const EstimatePanel = ({ estimate, prompt, onBuildCreated }) => {
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const {
    size_bucket,
    estimated_input_tokens,
    estimated_output_tokens,
    estimated_cost_usd,
    per_build_cap_usd,
    within_per_build_cap,
    daily_spent_usd,
    daily_cap_usd,
    daily_remaining_usd,
    within_daily_budget,
    within_budget,
  } = estimate;

  const handleConfirm = async () => {
    setCreating(true);
    try {
      const build = await createBuild(prompt);
      toast.success("Build encolado. Sigue el progreso en vivo abajo.");
      setOpen(false);
      onBuildCreated(build);
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="border border-[#4D7CFF]/30 bg-background p-4" data-testid="estimate-panel">
      <p className="font-heading text-lg font-black tracking-tighter">Costo estimado</p>

      <dl className="mt-3 grid grid-cols-2 gap-3 font-mono text-xs sm:grid-cols-3">
        <div>
          <dt className="text-muted-foreground">Costo estimado</dt>
          <dd className="text-sm text-foreground" data-testid="estimate-cost">
            {fmtUsd(estimated_cost_usd)}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Tamaño</dt>
          <dd className="text-sm text-foreground" data-testid="estimate-bucket">
            {BUCKET_LABELS[size_bucket] || size_bucket}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Tokens (entrada / salida)</dt>
          <dd className="text-sm text-foreground" data-testid="estimate-tokens">
            {estimated_input_tokens} / {estimated_output_tokens}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Tope por build</dt>
          <dd className="text-sm text-foreground">{fmtUsd(per_build_cap_usd)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Disponible hoy</dt>
          <dd className="text-sm text-foreground">{fmtUsd(daily_remaining_usd)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Gastado hoy / tope diario</dt>
          <dd className="text-sm text-foreground">
            {fmtUsd(daily_spent_usd)} / {fmtUsd(daily_cap_usd)}
          </dd>
        </div>
      </dl>

      {!within_budget && (
        <div
          className="mt-4 flex items-start gap-2 border-l-2 border-[#FF2A2A] bg-[#FF2A2A]/5 p-3"
          data-testid="estimate-budget-warning"
        >
          <WarningCircle size={18} className="mt-0.5 shrink-0 text-[#FF2A2A]" />
          <div className="text-xs text-muted-foreground">
            {!within_per_build_cap && (
              <p>
                El costo estimado ({fmtUsd(estimated_cost_usd)}) supera el tope máximo por build (
                {fmtUsd(per_build_cap_usd)}).
              </p>
            )}
            {!within_daily_budget && (
              <p>
                El presupuesto diario restante ({fmtUsd(daily_remaining_usd)} de {fmtUsd(daily_cap_usd)}) no alcanza
                para este build.
              </p>
            )}
            <p className="mt-1 text-foreground">Reduce el alcance del prompt o espera a que se libere presupuesto.</p>
          </div>
        </div>
      )}

      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogTrigger asChild>
          <Button className="mt-4 gap-2" disabled={!within_budget} data-testid="confirm-build-button">
            <RocketLaunch size={16} weight="bold" /> Confirmar y ejecutar
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent data-testid="confirm-build-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>¿Ejecutar este build?</AlertDialogTitle>
            <AlertDialogDescription>
              Esto va a consumir aproximadamente {fmtUsd(estimated_cost_usd)} de la API de Anthropic contra el
              presupuesto diario compartido. La ejecución no se puede deshacer una vez que el build empiece a correr.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="confirm-build-cancel">Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                // preventDefault: AlertDialogAction cierra el dialogo apenas se
                // hace click (envuelve Dialog.Close). Lo evitamos para poder
                // mostrar el estado "Encolando..." y cerrar solo tras exito.
                e.preventDefault();
                handleConfirm();
              }}
              disabled={creating}
              data-testid="confirm-build-action"
            >
              {creating ? "Encolando..." : "Sí, ejecutar build"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
