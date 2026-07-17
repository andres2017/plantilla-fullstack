// Pantalla de referencia con los 4 estados obligatorios de toda vista de
// listado en este template: cargando / vacio / error / exito (ver CLAUDE.md,
// regla del subagente frontend-senior). Para una entidad nueva: copia esta
// carpeta completa (api.js + esta pagina + components/) y ajusta los campos.
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { ArrowClockwise, DotsThree, Trash, WarningCircle } from "@phosphor-icons/react";
import { fetchItems, updateItem, deleteItem } from "./api";
import { getApiError } from "@/lib/api";
import { useAuth } from "@/features/auth/AuthContext";
import { ActiveBadge } from "./components/ActiveBadge";
import { CreateItemDialog } from "./components/CreateItemDialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function ItemsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [state, setState] = useState({ status: "loading", data: null, error: "" });
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setState((s) => ({ ...s, status: "loading" }));
    try {
      const data = await fetchItems({ page, limit: 10 });
      setState({ status: "success", data, error: "" });
    } catch (err) {
      setState({ status: "error", data: null, error: getApiError(err) });
    }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  const toggleActive = async (id, active) => {
    try {
      await updateItem(id, { active: !active });
      toast.success(!active ? "Item activado" : "Item desactivado");
      load();
    } catch (err) {
      toast.error(getApiError(err));
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteItem(id);
      toast.success("Item eliminado");
      load();
    } catch (err) {
      toast.error(getApiError(err));
    }
  };

  const pagination = state.data?.pagination;

  return (
    <div className="mx-auto max-w-5xl" data-testid="items-page">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-heading text-4xl font-black tracking-tighter">Items</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {pagination ? `${pagination.total} items registrados` : "Entidad de referencia del template"}
          </p>
        </div>
        {isAdmin && <CreateItemDialog onCreated={load} />}
      </div>

      <div className="mt-8 border border-border bg-card">
        {/* Estado: cargando */}
        {state.status === "loading" && (
          <div className="space-y-3 p-5" data-testid="items-loading-state">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full rounded-none" />
            ))}
          </div>
        )}

        {/* Estado: error */}
        {state.status === "error" && (
          <div className="flex flex-col items-start gap-4 border-l-2 border-[#FF2A2A] p-8" data-testid="items-error-state">
            <WarningCircle size={28} className="text-[#FF2A2A]" />
            <div>
              <p className="font-heading text-xl font-bold tracking-tight">Algo falló al cargar los items.</p>
              <p className="mt-1 font-mono text-xs text-muted-foreground">{state.error}</p>
            </div>
            <Button variant="outline" onClick={load} className="gap-2" data-testid="items-retry-button">
              <ArrowClockwise size={15} /> Reintentar
            </Button>
          </div>
        )}

        {/* Estado: vacio */}
        {state.status === "success" && state.data.items.length === 0 && (
          <div className="p-12 sm:p-16" data-testid="items-empty-state">
            <p className="font-heading text-2xl font-black tracking-tighter text-muted-foreground">
              Aún no hay items aquí.
            </p>
            <p className="mt-2 max-w-sm text-sm text-muted-foreground">
              {isAdmin
                ? "Crea tu primer item con el botón «Nuevo item»."
                : "Cuando el administrador cree items, aparecerán en esta lista."}
            </p>
          </div>
        )}

        {/* Estado: exito */}
        {state.status === "success" && state.data.items.length > 0 && (
          <Table data-testid="items-table">
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-xs uppercase tracking-[0.2em]">Nombre</TableHead>
                <TableHead className="text-xs uppercase tracking-[0.2em]">Descripción</TableHead>
                <TableHead className="text-xs uppercase tracking-[0.2em]">Estado</TableHead>
                {isAdmin && <TableHead className="w-12" />}
              </TableRow>
            </TableHeader>
            <TableBody>
              {state.data.items.map((item) => (
                <TableRow key={item.id} data-testid={`item-row-${item.id}`}>
                  <TableCell className="text-sm font-medium">{item.name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{item.description || "—"}</TableCell>
                  <TableCell><ActiveBadge active={item.active} /></TableCell>
                  {isAdmin && (
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8" data-testid={`item-actions-${item.id}`}>
                            <DotsThree size={18} weight="bold" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel className="text-xs uppercase tracking-widest">Acciones</DropdownMenuLabel>
                          <DropdownMenuItem onClick={() => toggleActive(item.id, item.active)} data-testid={`toggle-active-${item.id}`}>
                            {item.active ? "Desactivar" : "Activar"}
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-[#FF2A2A] focus:text-[#FF2A2A]"
                            onClick={() => handleDelete(item.id)} data-testid={`delete-item-${item.id}`}>
                            <Trash size={14} className="mr-2" /> Eliminar
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {pagination && pagination.total_pages > 1 && (
        <div className="mt-4 flex items-center justify-between" data-testid="items-pagination">
          <p className="font-mono text-xs text-muted-foreground">
            Página {pagination.page} de {pagination.total_pages}
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)} data-testid="pagination-prev-button">
              Anterior
            </Button>
            <Button variant="outline" size="sm" disabled={page >= pagination.total_pages}
              onClick={() => setPage((p) => p + 1)} data-testid="pagination-next-button">
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
