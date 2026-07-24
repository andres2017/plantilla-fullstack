// Catalogo compartido de tipos de entrega, agentes y modelos de la Fábrica
// Cyberandres. Fuente unica para TemplateTypePicker, AgentModelPicker,
// PromptComposer y BuildsPage — evita que cada componente invente su propia
// copia de labels/ids y que se desincronicen. Los `value` deben coincidir
// exactamente con los Literal de backend/builds/models/build.py.

export const TEMPLATE_TYPES = [
  {
    value: "full_stack",
    label: "App Full Stack",
    help: "Backend FastAPI + frontend React de la plantilla, conectados entre sí.",
  },
  {
    value: "web_landing",
    label: "Página web / Landing",
    help: "Una o pocas páginas de presentación, enfocado en frontend y contenido.",
  },
  {
    value: "mobile_apk",
    label: "App móvil (Capacitor/APK)",
    help: "Ajustes sobre la capa Capacitor para empaquetar como app Android.",
  },
  {
    value: "backend_only",
    label: "Solo API",
    help: "Cambios acotados a backend: routers, services, repositories.",
  },
  {
    value: "custom",
    label: "Libre / avanzado",
    help: "Sin restricción de alcance fija — describe exactamente qué tocar.",
  },
];

export const AGENTS = [
  {
    value: "implementer",
    label: "Implementador",
    help: "Implementa features sobre la plantilla (default).",
  },
  {
    value: "architect",
    label: "Arquitecto",
    help: "Diseña estructura y contratos, escribe poco código.",
  },
  {
    value: "reviewer",
    label: "Revisor",
    help: "Revisa y refactoriza sin agregar features nuevas.",
  },
  {
    value: "mobile",
    label: "Móvil",
    help: "Enfocado en Capacitor/Android.",
  },
  {
    value: "docs",
    label: "Documentación",
    help: "README, DECISIONS, comentarios.",
  },
];

export const MODELS = [
  {
    value: "haiku",
    label: "Rápido / barato",
    help: "Tareas chicas y acotadas.",
  },
  {
    value: "sonnet",
    label: "Equilibrado",
    help: "Default para features normales.",
  },
  {
    value: "opus",
    label: "Máxima calidad",
    help: "Arquitectura compleja o refactors grandes.",
  },
];

export const EXAMPLE_PROMPTS = {
  full_stack:
    "Agrega un módulo de facturación con lista, detalle y exportación a PDF, con su endpoint FastAPI y su pantalla en React conectados.",
  web_landing:
    "Crea una landing de una sola página para el lanzamiento del producto: hero, sección de features y formulario de contacto.",
  mobile_apk:
    "Ajusta la configuración de Capacitor para el splash screen y el ícono de la app, y sube el versionCode.",
  backend_only:
    "Agrega un endpoint GET /api/items/stats que devuelva el total de items y cuántos están activos.",
  custom:
    "Describe exactamente qué archivos tocar y cuáles no, con el nivel de detalle que necesites.",
};

// Heurística de recomendación (sugerencia visual, no bloquea nada): tareas
// chicas de solo-API rinden bien en el modelo rápido; prompts muy largos
// (refactors grandes) se benefician del modelo de máxima calidad; el resto
// usa el default equilibrado.
export function recommendModel(templateType, promptLength) {
  if (templateType === "backend_only" && promptLength > 0 && promptLength < 200) {
    return "haiku";
  }
  if (promptLength > 1500) {
    return "opus";
  }
  return "sonnet";
}
