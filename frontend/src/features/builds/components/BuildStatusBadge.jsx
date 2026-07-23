// Badge de estado de build — mismo patron que features/items/components/ActiveBadge.jsx
// (mapa status -> clases Tailwind), reutilizado entre QueueProgressCard y BuildHistoryTable.
const STATUS_CONFIG = {
  queued: { label: "en cola", className: "text-muted-foreground border-border bg-secondary" },
  running: { label: "ejecutando", className: "text-[#4D7CFF] border-[#4D7CFF]/40 bg-[#4D7CFF]/10" },
  completed: { label: "completado", className: "text-[#00E676] border-[#00E676]/40 bg-[#00E676]/10" },
  failed: { label: "fallido", className: "text-[#FF2A2A] border-[#FF2A2A]/40 bg-[#FF2A2A]/10" },
  cancelled: { label: "cancelado", className: "text-[#FFB300] border-[#FFB300]/40 bg-[#FFB300]/10" },
};

export const BuildStatusBadge = ({ status }) => {
  const cfg = STATUS_CONFIG[status] || { label: status || "—", className: "text-muted-foreground border-border" };
  return (
    <span
      className={`inline-block border px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.15em] ${cfg.className}`}
      data-testid={`build-status-badge-${status}`}
    >
      {cfg.label}
    </span>
  );
};
