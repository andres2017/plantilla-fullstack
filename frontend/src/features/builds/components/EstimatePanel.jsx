import { useMemo, useState } from "react";
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

export const EstimatePanel = ({
  estimate,
  prompt,
  onBuildCreated,
  budget = null,
  createPayload = {},
}) => {
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const estimated_cost_usd = estimate?.estimated_cost_usd ?? 0;
  const inputTok = estimate?.input_tokens_est ?? estimate?.estimated_input_tokens;
  const outputTok = estimate?.output_tokens_est ?? estimate?.estimated_output_tokens;

  const caps = useMemo(() => {
    const perBuild = Number(budget?.per_build_cap_usd ?? 0.5);
    const remaining = Number(budget?.remaining_usd ?? 20);
    const spent = Number(budget?.spent_usd ?? 0);
    const cap = Number(budget?.cap_usd ?? 20);
    const withinPer = estimated_cost_usd <= perBuild + 1e-9;
    const withinDaily = estimated_cost_usd <= remaining + 1e-9;
    return {
      per_build_cap_usd: perBuild,
      daily_remaining_usd: remaining,
      daily_spent_usd: spent,
      daily_cap_usd: cap,
      within_per_build_cap: withinPer,
      within_daily_budget: withinDaily,
      within_budget: withinPer && withinDaily,
    };
  }, [budget, estimated_cost_usd]);

  const handleConfirm = async () => {
    setCreating(true);
    try {
      const build = await createBuild({
        prompt,
        ...createPayload,
      });
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
          <dt className="text-muted-foreground">Tokens (entrada / salida)</dt>
          <dd className="text-sm text-foreground" data-testid="estimate-tokens">
            {inputTok ?? "—"} / {outputTok ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Tope por build</dt>
          <dd className="text-sm text-foreground">{fmtUsd(caps.per_build_cap_usd)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Disponible hoy</dt>
          <dd className="text-sm text-foreground">{fmtUsd(caps.daily_remaining_usd)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Gastado hoy / tope diario</dt>
          <dd className="text-sm text-foreground">
            {fmtUsd(caps.daily_spent_usd)} / {fmtUsd(caps.daily_cap_usd)}
          </dd>
        </div>
      </dl>

      {!caps.within_budget && (
        <div
          className="mt-4 flex items-start gap-2 border-l-2 border-[#FF2A2A] bg-[#FF2A2A]/5 p-3"
          data-testid="estimate-budget-warning"
        >
          <WarningCircle size={18} className="mt-0.5 shrink-0 text-[#FF2A2A]" />
          <div className="text-xs text-muted-foreground">
            {!caps.within_per_build_cap && (
              <p>
                El costo estimado ({fmtUsd(estimated_cost_usd)}) supera el tope por build (
                {fmtUsd(caps.per_build_cap_usd)}).
              </p>
            )}
            {!caps.within_daily_budget && (
              <p>
                El presupuesto diario restante ({fmtUsd(caps.daily_remaining_usd)}) no alcanza para este build.
              </p>
            )}
          </div>
        </div>
      )}

      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogTrigger asChild>
          <Button className="mt-4 gap-2" disabled={!caps.within_budget} data-testid="confirm-build-button">
            <RocketLaunch size={16} weight="bold" /> Confirmar y ejecutar
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent data-testid="confirm-build-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>¿Ejecutar este build?</AlertDialogTitle>
            <AlertDialogDescription>
              Esto consumirá aproximadamente {fmtUsd(estimated_cost_usd)} del presupuesto del día.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="confirm-build-cancel">Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
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
