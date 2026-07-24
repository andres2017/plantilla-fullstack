// Tabla paginada de builds — mismo patron de maquina de estados y data-testid
// que features/items/ItemsPage.jsx (cargando/vacio/error/exito). `refreshKey`
// permite al padre forzar un reload (build recien creado o terminado) sin
// levantar el estado de paginacion hasta BuildsPage.
import { useCallback, useEffect, useState } from "react";
import { ArrowClockwise, DownloadSimple, WarningCircle } from "@phosphor-icons/react";
import { buildDownloadUrl, fetchBuilds } from "../api";
import { getApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { BuildStatusBadge } from "./BuildStatusBadge";
import { TEMPLATE_TYPES, AGENTS, MODELS } from "../constants";

const PAGE_SIZE = 10;

const fmtUsd = (v) => (v == null ? "—" : `$${Number(v).toFixed(4)}`);

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" }) : "—");

const truncate = (text, max = 60) => (text && text.length > max ? `${text.slice(0, max)}…` : text || "—");

const shortLabel = (list, value) => list.find((item) => item.value === value)?.label || value || "—";

export const BuildHistoryTable = ({ refreshKey = 0 }) => {
  const [state, setState] = useState({ status: "loading", data: null, error: "" });
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setState((s) => ({ ...s, status: "loading" }));
    try {
      const data = await fetchBuilds({ page, limit: PAGE_SIZE });
      setState({ status: "success", data, error: "" });
    } catch (err) {
      setState({ status: "error", data: null, error: getApiError(err) });
    }
  }, [page]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const pagination = state.data?.pagination;

  return (
    <TooltipProvider delayDuration={200}>
      <div data-testid="build-history">
        <p className="font-heading text-lg font-black tracking-tighter">Historial de builds</p>

        <div className="mt-3 overflow-x-auto border border-border bg-card">
          {/* Estado: cargando */}
          {state.status === "loading" && (
            <div className="space-y-3 p-5" data-testid="build-history-loading-state">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full rounded-none" />
              ))}
            </div>
          )}

          {/* Estado: error */}
          {state.status === "error" && (
            <div className="flex flex-col items-start gap-4 border-l-2 border-[#FF2A2A] p-8" data-testid="build-history-error-state">
              <WarningCircle size={28} className="text-[#FF2A2A]" />
              <div>
                <p className="font-heading text-xl font-bold tracking-tight">Algo falló al cargar el historial de builds.</p>
                <p className="mt-1 font-mono text-xs text-muted-foreground">{state.error}</p>
              </div>
              <Button variant="outline" onClick={load} className="gap-2" data-testid="build-history-retry-button">
                <ArrowClockwise size={15} /> Reintentar
              </Button>
            </div>
          )}

          {/* Estado: vacio */}
          {state.status === "success" && state.data.items.length === 0 && (
            <div className="p-12 sm:p-16" data-testid="build-history-empty-state">
              <p className="font-heading text-2xl font-black tracking-tighter text-muted-foreground">
                Aún no se ha ejecutado ningún build.
              </p>
              <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                Escribe un prompt arriba, calcula el costo estimado y confirma para lanzar el primero.
              </p>
            </div>
          )}

          {/* Estado: exito */}
          {state.status === "success" && state.data.items.length > 0 && (
            <Table data-testid="build-history-table">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="text-xs uppercase tracking-[0.2em]">Fecha</TableHead>
                  <TableHead className="text-xs uppercase tracking-[0.2em]">Prompt</TableHead>
                  <TableHead className="text-xs uppercase tracking-[0.2em]">Tipo / agente / modelo</TableHead>
                  <TableHead className="text-xs uppercase tracking-[0.2em]">Estado</TableHead>
                  <TableHead className="text-xs uppercase tracking-[0.2em]">Costo est. / real</TableHead>
                  <TableHead className="text-xs uppercase tracking-[0.2em]">Disparado por</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {state.data.items.map((build) => (
                  <TableRow key={build.id} data-testid={`build-row-${build.id}`}>
                    <TableCell className="whitespace-nowrap text-sm text-muted-foreground">{fmtDate(build.created_at)}</TableCell>
                    <TableCell className="max-w-xs text-sm font-medium">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="cursor-help" tabIndex={0}>
                            {truncate(build.prompt)}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-sm whitespace-pre-wrap">{build.prompt}</TooltipContent>
                      </Tooltip>
                    </TableCell>
                    <TableCell className="whitespace-nowrap font-mono text-[11px] text-muted-foreground" data-testid={`build-config-${build.id}`}>
                      {shortLabel(TEMPLATE_TYPES, build.template_type)}
                      <br />
                      {shortLabel(AGENTS, build.agent)} · {shortLabel(MODELS, build.model)}
                    </TableCell>
                    <TableCell>
                      {build.status === "failed" && build.error_message ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="inline-flex cursor-help items-center gap-1.5" tabIndex={0}>
                              <BuildStatusBadge status={build.status} />
                              <WarningCircle size={14} className="text-[#FF2A2A]" />
                            </span>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-sm whitespace-pre-wrap">
                            {build.error_code && (
                              <p className="font-mono text-[10px] text-muted-foreground">{build.error_code}</p>
                            )}
                            <p>{build.error_message}</p>
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        <BuildStatusBadge status={build.status} />
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap font-mono text-xs text-muted-foreground">
                      {fmtUsd(build.estimated_cost_usd)} / {fmtUsd(build.actual_cost_usd)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{build.created_by_email || "—"}</TableCell>
                    <TableCell>
                      {build.has_zip ? (
                        <Button asChild variant="outline" size="icon" className="h-8 w-8" data-testid={`download-build-${build.id}`}>
                          <a href={buildDownloadUrl(build.id)} download aria-label={`Descargar resultado del build ${build.id}`}>
                            <DownloadSimple size={15} />
                          </a>
                        </Button>
                      ) : (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span>
                              <Button
                                variant="outline"
                                size="icon"
                                className="h-8 w-8"
                                disabled
                                aria-label="Descarga no disponible"
                                data-testid={`download-build-${build.id}-disabled`}
                              >
                                <DownloadSimple size={15} />
                              </Button>
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            {build.status === "completed" ? "El zip expiró (redeploy o limpieza)" : "Todavía no hay zip disponible"}
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        {pagination && pagination.total_pages > 1 && (
          <div className="mt-4 flex items-center justify-between" data-testid="build-history-pagination">
            <p className="font-mono text-xs text-muted-foreground">
              Página {pagination.page} de {pagination.total_pages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                data-testid="build-history-prev-button"
              >
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= pagination.total_pages}
                onClick={() => setPage((p) => p + 1)}
                data-testid="build-history-next-button"
              >
                Siguiente
              </Button>
            </div>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
};
