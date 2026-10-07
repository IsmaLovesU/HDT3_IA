// Verifica que las herramientas se llamaron en la secuencia esperada (sin contar otras).
// Variable del caso: secuencia = "consultar_clima,agendar_cita" (en ese orden).
// Si secuencia = "" no debe haberse llamado ninguna de las herramientas de la lista de control.

const CONTROL = ["consultar_clima", "agendar_cita"];

module.exports = (output, context) => {
  const esperada = (context.vars.secuencia ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const llamadas = (context.providerResponse?.metadata?.toolCalls ?? [])
    .map((t) => t.name)
    .filter((n) => CONTROL.includes(n));

  const iguales =
    esperada.length === llamadas.length && esperada.every((nombre, i) => nombre === llamadas[i]);

  return {
    pass: iguales,
    score: iguales ? 1 : 0,
    reason: iguales
      ? `Secuencia correcta: [${llamadas.join(" -> ") || "ninguna"}]`
      : `Se esperaba [${esperada.join(" -> ") || "ninguna"}] y se obtuvo [${llamadas.join(" -> ") || "ninguna"}]`,
  };
};
