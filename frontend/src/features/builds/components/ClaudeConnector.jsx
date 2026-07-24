import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { PlugsConnected, Plugs, Eye, EyeSlash, Trash } from "@phosphor-icons/react";
import { fetchLlmStatus, saveLlmKey, deleteLlmKey, setLlmModel } from "../api";
import { getApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { t } from "../i18n";

export const ClaudeConnector = ({ locale = "es", onStatusChange }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [model, setModel] = useState("sonnet");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchLlmStatus();
      setStatus(data);
      setModel(data.preferred_model || "sonnet");
      onStatusChange?.(data);
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setLoading(false);
    }
  }, [onStatusChange]);

  useEffect(() => {
    load();
  }, [load]);

  const handleConnect = async (e) => {
    e.preventDefault();
    if (!apiKey.trim()) return;
    setSaving(true);
    try {
      const data = await saveLlmKey({ api_key: apiKey.trim(), preferred_model: model });
      setStatus(data);
      setApiKey("");
      setOpen(false);
      onStatusChange?.(data);
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
      onStatusChange?.(data);
      toast.success(locale === "en" ? "Disconnected" : "Desconectado");
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const handleModelChange = async (id) => {
    setModel(id);
    if (!status?.connected) return;
    try {
      const data = await setLlmModel(id);
      setStatus(data);
      onStatusChange?.(data);
    } catch (err) {
      toast.error(getApiError(err));
    }
  };

  if (loading && !status) {
    return (
      <div className="border border-border bg-card p-4 text-sm text-muted-foreground" data-testid="claude-connector-loading">
        {t(locale, "loading")}
      </div>
    );
  }

  const connected = Boolean(status?.connected);
  const models = status?.models || [];

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
            {status?.source === "env" && (
              <p className="mt-1 text-[11px] text-amber-400/90">
                {locale === "en"
                  ? "Using server env key (dev). Save your own key to use BYOK."
                  : "Usando key del servidor (dev). Guarda la tuya para BYOK."}
              </p>
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

      {models.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {models.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => handleModelChange(m.id)}
              className={`rounded border px-2.5 py-1 text-xs transition ${
                model === m.id
                  ? "border-primary bg-primary/10 text-foreground"
                  : "border-border text-muted-foreground hover:border-primary/50"
              }`}
              data-testid={`model-${m.id}`}
            >
              {locale === "en" ? m.label_en : m.label_es}
            </button>
          ))}
        </div>
      )}

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
                data-testid="claude-api-key-input"
              />
              <Button type="button" variant="outline" size="icon" onClick={() => setShowKey((v) => !v)}>
                {showKey ? <EyeSlash size={16} /> : <Eye size={16} />}
              </Button>
            </div>
            <p className="mt-1.5 text-[11px] text-muted-foreground">
              {locale === "en"
                ? "Get a key at console.anthropic.com → API keys. Usage is billed to your Anthropic account."
                : "Consigue una key en console.anthropic.com → API keys. El uso se cobra en tu cuenta de Anthropic."}
            </p>
          </div>
          <Button type="submit" disabled={saving || apiKey.trim().length < 20} data-testid="claude-connect-submit">
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
