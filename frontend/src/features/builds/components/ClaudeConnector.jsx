import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { PlugsConnected, Plugs, Eye, EyeSlash, Trash } from "@phosphor-icons/react";
import { fetchLlmStatus, saveLlmKey, deleteLlmKey, setLlmModel } from "../api";
import { getApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { t } from "../i18n";

const STORAGE_KEY = "fabrica_model";

const FALLBACK_MODELS = [
  {
    id: "haiku",
    name: "Haiku 4.5",
    desc_es: "Más rápido · ideal para guías y cambios pequeños",
    desc_en: "Fastest · great for guides and small edits",
  },
  {
    id: "sonnet",
    name: "Sonnet 5",
    desc_es: "Equilibrado · recomendado para el día a día",
    desc_en: "Balanced · recommended for daily work",
  },
  {
    id: "opus",
    name: "Opus 4.8",
    desc_es: "Máxima calidad · tareas difíciles / arquitectura",
    desc_en: "Highest quality · hard tasks / architecture",
  },
];

function readStoredModel() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "haiku" || v === "sonnet" || v === "opus") return v;
  } catch {
    /* ignore */
  }
  return "sonnet";
}

export const ClaudeConnector = ({ locale = "es", onStatusChange }) => {
  const onStatusChangeRef = useRef(onStatusChange);
  useEffect(() => {
    onStatusChangeRef.current = onStatusChange;
  }, [onStatusChange]);

  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [model, setModel] = useState(readStoredModel);
  const [saving, setSaving] = useState(false);
  const userPickedRef = useRef(false);

  // Solo al montar: no re-fetch cuando el padre re-renderiza
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await fetchLlmStatus();
        if (cancelled) return;
        setStatus(data);
        const stored = readStoredModel();
        const preferred =
          userPickedRef.current || stored !== "sonnet"
            ? stored
            : data.preferred_model || stored;
        const finalModel =
          preferred === "haiku" || preferred === "sonnet" || preferred === "opus"
            ? preferred
            : "sonnet";
        setModel(finalModel);
        try {
          localStorage.setItem(STORAGE_KEY, finalModel);
        } catch {
          /* ignore */
        }
        onStatusChangeRef.current?.({ ...data, preferred_model: finalModel });
      } catch (err) {
        if (!cancelled) toast.error(getApiError(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleConnect = async (e) => {
    e.preventDefault();
    if (!apiKey.trim()) return;
    setSaving(true);
    try {
      const data = await saveLlmKey({ api_key: apiKey.trim(), preferred_model: model });
      setStatus(data);
      setApiKey("");
      setOpen(false);
      onStatusChangeRef.current?.(data);
      toast.success(locale === "en" ? "Claude connected" : "Claude conectado");
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDisconnect = async () => {
    setSaving(true);
    try {
      const data = await deleteLlmKey();
      setStatus(data);
      onStatusChangeRef.current?.(data);
      toast.success(locale === "en" ? "Disconnected" : "Desconectado");
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const handleModelChange = async (id) => {
    if (id !== "haiku" && id !== "sonnet" && id !== "opus") return;
    userPickedRef.current = true;
    setModel(id);
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* ignore */
    }
    onStatusChangeRef.current?.({
      ...(status || { connected: false }),
      preferred_model: id,
      connected: Boolean(status?.connected),
    });

    try {
      const data = await setLlmModel(id);
      setStatus(data);
      // No pisar la elección local si el server devuelve otro valor viejo
      onStatusChangeRef.current?.({ ...data, preferred_model: id });
    } catch {
      // La UI ya muestra el modelo elegido; el build usa preferredModel del padre
    }
  };

  if (loading && !status) {
    return (
      <div className="border border-border bg-card p-4 text-sm text-muted-foreground">
        {t(locale, "loading")}
      </div>
    );
  }

  const connected = Boolean(status?.connected);
  const models = status?.models?.length ? status.models : FALLBACK_MODELS;

  return (
    <div className="border border-border bg-card p-4" data-testid="claude-connector">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          {connected ? (
            <PlugsConnected size={22} className="mt-0.5 text-emerald-400" weight="fill" />
          ) : (
            <Plugs size={22} className="mt-0.5 text-amber-400" />
          )}
          <div>
            <p className="font-heading text-sm font-bold tracking-tight">
              {connected
                ? locale === "en"
                  ? "Claude connected"
                  : "Claude conectado"
                : locale === "en"
                  ? "Connect your Claude"
                  : "Conecta tu Claude"}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {locale === "en" ? status?.hint_en : status?.hint_es}
            </p>
            {status?.key_masked && (
              <p className="mt-1 font-mono text-[11px] text-muted-foreground">{status.key_masked}</p>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {connected && status?.source === "user" && (
            <Button variant="outline" size="sm" onClick={handleDisconnect} disabled={saving} className="gap-1">
              <Trash size={14} />
              {locale === "en" ? "Disconnect" : "Desconectar"}
            </Button>
          )}
          <Button size="sm" variant={connected ? "outline" : "default"} onClick={() => setOpen((v) => !v)}>
            {connected
              ? locale === "en"
                ? "Update key"
                : "Cambiar key"
              : locale === "en"
                ? "Connect"
                : "Conectar"}
          </Button>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <p className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
          {locale === "en" ? "Claude model" : "Modelo Claude"}
        </p>
        <div className="grid gap-2 sm:grid-cols-3">
          {models.map((m) => {
            const selected = model === m.id;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => handleModelChange(m.id)}
                className={`cursor-pointer rounded border px-3 py-2.5 text-left transition ${
                  selected
                    ? "border-primary bg-primary/10 ring-1 ring-primary/40"
                    : "border-border hover:border-primary/40"
                }`}
                data-testid={`model-${m.id}`}
              >
                <p className="text-sm font-semibold tracking-tight">{m.name || m.label_es || m.id}</p>
                <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                  {locale === "en" ? m.desc_en || m.label_en : m.desc_es || m.label_es}
                </p>
              </button>
            );
          })}
        </div>
        <p className="text-[11px] text-muted-foreground">
          {locale === "en" ? "Selected: " : "Seleccionado: "}
          <span className="font-mono text-foreground">{model}</span>
        </p>
      </div>

      {open && (
        <form onSubmit={handleConnect} className="mt-4 space-y-3 border-t border-border pt-4">
          <div>
            <Label htmlFor="claude-api-key" className="text-xs uppercase tracking-[0.15em]">
              API key (Anthropic)
            </Label>
            <div className="mt-1 flex gap-2">
              <Input
                id="claude-api-key"
                type={showKey ? "text" : "password"}
                autoComplete="off"
                placeholder="sk-ant-…"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="font-mono text-sm"
              />
              <Button type="button" variant="outline" size="icon" onClick={() => setShowKey((v) => !v)}>
                {showKey ? <EyeSlash size={16} /> : <Eye size={16} />}
              </Button>
            </div>
          </div>
          <Button type="submit" disabled={saving || apiKey.trim().length < 20}>
            {saving
              ? t(locale, "loading")
              : locale === "en"
                ? "Save and connect"
                : "Guardar y conectar"}
          </Button>
        </form>
      )}
    </div>
  );
};
