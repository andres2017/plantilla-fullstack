import { useEffect, useRef, useState } from "react";
import { buildEventsUrl } from "../api";

const TERMINAL_STATUSES = ["completed", "failed", "cancelled"];

/**
 * Encapsula el ciclo de vida del canal SSE de progreso en vivo de un build
 * (GET /builds/{id}/events). Logica compartida extraida a custom hook para
 * que los componentes de presentacion (QueueProgressCard) solo consuman
 * estado derivado, sin manejar EventSource directamente.
 *
 * Eventos nombrados del contrato (NO onmessage):
 *  - "snapshot" -> {status, queue_position, progress_log:[{ts,message}]} (una vez, al conectar)
 *  - "progress" -> {ts, message} (se agrega al log en vivo)
 *  - "status"   -> {status, queue_position}
 *  - "done"     -> {status, cost_real_usd, download_url} (cierra el canal)
 *
 * Cierra el EventSource en cleanup, al recibir "done", o al llegar a un
 * estado terminal via "snapshot"/"status" (build ya terminado cuando el
 * admin reconecta/refresca la pestaña) — nunca deja conexiones colgadas.
 */
export const useBuildEvents = (buildId, { onDone } = {}) => {
  const [status, setStatus] = useState(null);
  const [queuePosition, setQueuePosition] = useState(null);
  const [log, setLog] = useState([]);
  const [connected, setConnected] = useState(false);
  const [result, setResult] = useState(null);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  useEffect(() => {
    if (!buildId) return undefined;

    setStatus(null);
    setQueuePosition(null);
    setLog([]);
    setConnected(false);
    setResult(null);

    let finished = false;
    const es = new EventSource(buildEventsUrl(buildId), { withCredentials: true });

    const finish = (payload) => {
      if (finished) return;
      finished = true;
      setResult(payload || null);
      es.close();
      onDoneRef.current?.(payload);
    };

    es.addEventListener("snapshot", (e) => {
      const data = JSON.parse(e.data);
      setConnected(true);
      setStatus(data.status);
      setQueuePosition(data.queue_position ?? null);
      setLog(data.progress_log || []);
      if (TERMINAL_STATUSES.includes(data.status)) finish(data);
    });

    es.addEventListener("progress", (e) => {
      const data = JSON.parse(e.data);
      setLog((prev) => [...prev, data]);
    });

    es.addEventListener("status", (e) => {
      const data = JSON.parse(e.data);
      setStatus(data.status);
      setQueuePosition(data.queue_position ?? null);
      if (TERMINAL_STATUSES.includes(data.status)) finish(data);
    });

    es.addEventListener("done", (e) => {
      const data = JSON.parse(e.data);
      setStatus(data.status || "completed");
      finish(data);
    });

    es.onopen = () => setConnected(true);
    // El navegador reintenta EventSource solo; no mostramos toast en cada
    // blip de red, solo reflejamos "desconectado" mientras reintenta.
    es.onerror = () => setConnected(false);

    return () => {
      finished = true;
      es.close();
    };
  }, [buildId]);

  return { status, queuePosition, log, connected, result };
};
