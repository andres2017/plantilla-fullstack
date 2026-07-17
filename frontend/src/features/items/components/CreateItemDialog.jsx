// Dialogo de creacion — duplica este patron (Dialog + form controlado + toast)
// para el formulario de creacion de tu propia entidad.
import { useState } from "react";
import { toast } from "sonner";
import { createItem } from "../api";
import { getApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger,
} from "@/components/ui/dialog";
import { Plus } from "@phosphor-icons/react";

export const CreateItemDialog = ({ onCreated }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await createItem({ name: form.name, description: form.description || undefined });
      toast.success("Item creado");
      setOpen(false);
      setForm({ name: "", description: "" });
      onCreated();
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2" data-testid="open-create-item-dialog">
          <Plus size={16} weight="bold" /> Nuevo item
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md" data-testid="create-item-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading text-2xl font-black tracking-tighter">Crear item</DialogTitle>
          <DialogDescription>Entidad de referencia — duplica este flujo para tus propios recursos.</DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={submit}>
          <div className="space-y-2">
            <Label className="text-xs uppercase tracking-[0.2em]">Nombre</Label>
            <Input required minLength={2} value={form.name} placeholder="Ej: Primer item"
              onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="item-name-input" />
          </div>
          <div className="space-y-2">
            <Label className="text-xs uppercase tracking-[0.2em]">Descripcion (opcional)</Label>
            <Input value={form.description} placeholder="Detalle breve"
              onChange={(e) => setForm({ ...form, description: e.target.value })} data-testid="item-description-input" />
          </div>
          <Button type="submit" disabled={loading} className="w-full" data-testid="submit-create-item">
            {loading ? "Creando..." : "Crear item"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};
