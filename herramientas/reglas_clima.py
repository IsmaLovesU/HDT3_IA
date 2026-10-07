"""Criterio de seguridad para saltar según el pronóstico diario.

Función pura: no hace llamadas de red, así que es fácil de probar.
"""

from dataclasses import dataclass

IDEAL = "ideal"
MARGINAL = "marginal"
PROHIBIDO = "prohibido"

# Umbrales en km/h, mm y %, según el criterio del cliente.
VIENTO_IDEAL_MAX = 20.0
VIENTO_PROHIBIDO_MIN = 28.0  # > 28 km/h
RAFAGAS_PROHIBIDO_MIN = 35.0  # > 35 km/h
NUBOSIDAD_IDEAL_MAX = 30.0  # < 30 %
NUBOSIDAD_PROHIBIDO_MIN = 75.0  # > 75 %


@dataclass(frozen=True)
class Pronostico:
    fecha: str
    viento_superficie_kmh: float  # wind_speed_10m_max
    rafagas_kmh: float  # wind_gusts_10m_max
    precipitacion_mm: float  # precipitation_sum
    nubosidad_pct: float  # cloud_cover_mean
    temperatura_max_c: float  # temperature_2m_max (informativa, no entra al criterio)


@dataclass(frozen=True)
class Evaluacion:
    nivel: str
    motivos: tuple[str, ...]

    @property
    def permite_agendar(self) -> bool:
        """Sólo un día ideal se agenda sin confirmación. Un día marginal requiere confirmación explícita."""
        return self.nivel == IDEAL


def evaluar(pronostico: Pronostico) -> Evaluacion:
    prohibidos: list[str] = []
    marginales: list[str] = []

    viento = pronostico.viento_superficie_kmh
    if viento > VIENTO_PROHIBIDO_MIN:
        prohibidos.append(f"viento en superficie {viento} km/h (> {VIENTO_PROHIBIDO_MIN:g})")
    elif viento >= VIENTO_IDEAL_MAX:
        marginales.append(f"viento en superficie {viento} km/h (rango marginal 20–28)")

    if pronostico.rafagas_kmh > RAFAGAS_PROHIBIDO_MIN:
        prohibidos.append(f"ráfagas {pronostico.rafagas_kmh} km/h (> {RAFAGAS_PROHIBIDO_MIN:g})")

    if pronostico.precipitacion_mm > 0.0:
        prohibidos.append(f"precipitación {pronostico.precipitacion_mm} mm (> 0)")

    nubes = pronostico.nubosidad_pct
    if nubes > NUBOSIDAD_PROHIBIDO_MIN:
        prohibidos.append(f"cobertura de nubes {nubes} % (> {NUBOSIDAD_PROHIBIDO_MIN:g})")
    elif nubes >= NUBOSIDAD_IDEAL_MAX:
        marginales.append(f"cobertura de nubes {nubes} % (rango marginal 30–75)")

    if prohibidos:
        return Evaluacion(PROHIBIDO, tuple(prohibidos + marginales))
    if marginales:
        return Evaluacion(MARGINAL, tuple(marginales))
    return Evaluacion(IDEAL, ())
