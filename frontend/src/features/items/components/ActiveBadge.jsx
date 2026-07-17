// Badge de estado simple (activo/inactivo). Si tu entidad tiene mas de 2
// estados, sigue el mismo patron: un mapa status -> clases Tailwind.
const styles = {
  true: "text-[#00E676] border-[#00E676]/40 bg-[#00E676]/10",
  false: "text-[#FF2A2A] border-[#FF2A2A]/40 bg-[#FF2A2A]/10",
};

export const ActiveBadge = ({ active }) => (
  <span
    className={`inline-block border px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.15em] ${styles[active]}`}
    data-testid={`active-badge-${active}`}
  >
    {active ? "activo" : "inactivo"}
  </span>
);
