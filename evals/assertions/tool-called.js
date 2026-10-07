// Aserción de tool execution: revisa las herramientas que el agente invocó.
//
// Variables del caso de prueba:
//   expected_tool:      "nombre" -> debe haberse llamado esa herramienta.
//                       "none"   -> no debe haberse llamado ninguna herramienta.
//                       "not:nombre" -> puede llamar otras, pero NO esa herramienta.
//   tool_args_pattern:  (opcional) regex que deben cumplir los argumentos serializados.

module.exports = (output, context) => {
  const expectedTool = context.vars.expected_tool;
  const argsPattern = context.vars.tool_args_pattern;
  const toolCalls = context.providerResponse?.metadata?.toolCalls ?? [];
  const nombres = toolCalls.map((t) => t.name).join(", ") || "ninguna";

  if (expectedTool === "none") {
    return {
      pass: toolCalls.length === 0,
      score: toolCalls.length === 0 ? 1 : 0,
      reason:
        toolCalls.length === 0
          ? "El agente respondió sin invocar herramientas, como se esperaba."
          : `Se invocaron herramientas no esperadas: ${nombres}`,
    };
  }

  if (expectedTool.startsWith("not:")) {
    const prohibida = expectedTool.slice(4);
    const invocada = toolCalls.some((t) => t.name === prohibida);
    return {
      pass: !invocada,
      score: invocada ? 0 : 1,
      reason: invocada
        ? `Se invocó "${prohibida}", que no debía llamarse. Herramientas: ${nombres}`
        : `"${prohibida}" no se invocó, como se esperaba.`,
    };
  }

  const match = toolCalls.find((t) => t.name === expectedTool);
  if (!match) {
    return {
      pass: false,
      score: 0,
      reason: `No se invocó "${expectedTool}". Herramientas invocadas: ${nombres}`,
    };
  }

  if (argsPattern && !new RegExp(argsPattern, "i").test(JSON.stringify(match.arguments ?? {}))) {
    return {
      pass: false,
      score: 0.5,
      reason: `"${expectedTool}" se invocó, pero los argumentos ${JSON.stringify(
        match.arguments
      )} no cumplen /${argsPattern}/`,
    };
  }

  return { pass: true, score: 1, reason: `"${expectedTool}" se invocó correctamente.` };
};
