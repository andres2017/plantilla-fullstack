// Se activa tras crear un build (o al reengancharse a uno queued/running que
// ya estaba en curso al cargar la pagina). Conectado al SSE via el hook
// useBuildEvents; muestra estado, posicion en cola, log de progreso en vivo
// con auto-scroll, y boton "Cancelar" mientras sea cancelable.
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { CircleNotch, Prohibit } from "@phosphor-icons/react";
import { cancelBuild } from "../api";
import { getApiError } from "@/lib/api";
import { useBuildEvents } from "../hooks/useBuildEvents";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BuildStatusBadge } from "./BuildStatusBadge";

const CANCELABLE = new Set(["queued", "running"]);

const fmtUsd = (v) => (v == null ? "—" : `$${Number(v).toFixed(4)}`);

export const QueueProgressCard = ({ buildId, onFinished }) => {
  const { status, queuePosition, log, connected, result } = useBuildEvents(buildId, { onDone: onFinished });
  const [cancelling, setCancelling] = useState(false);
  const logEndRef = useRef(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [log]);

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await cancelBuild(buildId);
      toast.success("Se solicitó la cancelación del build.");
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setCancelling(false);
    }
  };

  return (
    <Card className="border-[#4D7CFF]/40" data-testid="queue-progress-card">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 space-y-0">
        <div>
          <CardTitle className="font-heading text-xl font-black tracking-tighter">Build en curso</CardTitle>
          <CardDescription className="flex items-center gap-1.5">
            {!connected && <CircleNotch size={12} className="animate-spin" aria-hidden />}
            <span data-testid="queue-progress-connection">{connected ? "Conectado al progreso en vivo" : "Conectando…"}</span>
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          {status && <BuildStatusBadge status={status} />}
          {status === "queued" && queuePosition != null && (
            <span className="font-mono text-xs text-muted-foreground" data-testid="queue-progress-position">
              Posición: {queuePosition}
            </span>
          )}
          {CANCELABLE.has(status) && (
            <Button
              variant="destructive"
              size="sm"
              className="gap-2"
              disabled={cancelling}
              onClick={handleCancel}
              data-testid="cancel-build-button"
            >
              <Prohibit size={14} /> {cancelling ? "Cancelando..." : "Cancelar"}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div
          className="h-56 overflow-y-auto border border-border bg-background p-3 font-mono text-xs"
          data-testid="build-progress-log"
          role="log"
          aria-live="polite"
        >
          {log.length === 0 ? (
            <p className="text-muted-foreground">{connected ? "Sin eventos de progreso todavía." : "Esperando conexión..."}</p>
          ) : (
            log.map((entry, i) => (
              <p key={i} className="py-0.5 text-muted-foreground">
                <span className="text-[#4D7CFF]">[{new Date(entry.ts).toLocaleTimeString("es-CO")}]</span> {entry.message}
              </p>
            ))
          )}
          <div ref={logEndRef} />
        </div>

        {result && (
          <p className="mt-3 font-mono text-xs text-muted-foreground" data-testid="build-result-summary">
            {status === "completed" && `Terminado — costo real ${fmtUsd(result.cost_real_usd)}. Descárgalo desde el historial abajo.`}
            {status === "failed" && "El build falló. Revisa el historial para más detalle."}
            {status === "cancelled" && "El build fue cancelado."}
          </p>
        )}
      </CardContent>
    </Card>
  );
};
