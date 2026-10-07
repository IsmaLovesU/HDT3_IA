"""Integraciones externas del agente: FAQ, clima (Open-Meteo) y calendario de citas.

Son funciones planas que devuelven diccionarios. Las arquitecturas no las conocen
directamente: las usan a través de `herramientas/tools.py`, así que cambiar una
integración no obliga a tocar las tres arquitecturas.
"""

import json
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from herramientas.reglas_clima import PROHIBIDO, Evaluacion, Pronostico, evaluar

# Coordenadas del lugar de aterrizaje (Puerto San José / pista del evento).
LATITUD = 14.013722
LONGITUD = -90.771611
ZONA_HORARIA = "America/Guatemala"
DIAS_PRONOSTICO_MAX = 16  # Open-Meteo sólo ofrece 16 días de predicción.
URL_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
VARIABLES_DIARIAS = (
    "wind_speed_10m_max,wind_gusts_10m_max,precipitation_sum,"
    "cloud_cover_mean,temperature_2m_max"
)
ARCHIVO_CITAS = Path("data/citas.json")

PATRON_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def hoy_local() -> date:
    return datetime.now(ZoneInfo(ZONA_HORARIA)).date()


def validar_fecha(fecha_iso: str, hoy: date | None = None) -> date:
    """Valida que la fecha sea hoy o futura y dentro del horizonte de 16 días."""
    try:
        fecha = date.fromisoformat(fecha_iso)
    except ValueError as error:
        raise ValueError(f"La fecha '{fecha_iso}' no tiene formato AAAA-MM-DD.") from error

    hoy = hoy or hoy_local()
    if fecha < hoy:
        raise ValueError(f"La fecha {fecha_iso} ya pasó. Elige una fecha a partir de hoy ({hoy}).")

    limite = hoy + timedelta(days=DIAS_PRONOSTICO_MAX)
    if fecha > limite:
        raise ValueError(
            f"No se puede agendar el {fecha_iso}: el pronóstico sólo cubre hasta {limite} "
            f"({DIAS_PRONOSTICO_MAX} días). Elige una fecha dentro de ese rango."
        )
    return fecha


def _descargar_pronostico(fecha: date) -> dict:
    parametros = {
        "latitude": LATITUD,
        "longitude": LONGITUD,
        "daily": VARIABLES_DIARIAS,
        "timezone": ZONA_HORARIA,
        "start_date": fecha.isoformat(),
        "end_date": fecha.isoformat(),
    }
    url = f"{URL_OPEN_METEO}?{urllib.parse.urlencode(parametros)}"
    with urllib.request.urlopen(url, timeout=10) as respuesta:
        return json.load(respuesta)


def obtener_pronostico(
    fecha: date, descargar: Callable[[date], dict] = _descargar_pronostico
) -> Pronostico:
    datos = descargar(fecha)["daily"]
    return Pronostico(
        fecha=fecha.isoformat(),
        viento_superficie_kmh=datos["wind_speed_10m_max"][0],
        rafagas_kmh=datos["wind_gusts_10m_max"][0],
        precipitacion_mm=datos["precipitation_sum"][0],
        nubosidad_pct=datos["cloud_cover_mean"][0],
        temperatura_max_c=datos["temperature_2m_max"][0],
    )


def consultar_clima(fecha_iso: str, descargar: Callable[[date], dict] = _descargar_pronostico) -> dict:
    fecha = validar_fecha(fecha_iso)
    pronostico = obtener_pronostico(fecha, descargar)
    evaluacion: Evaluacion = evaluar(pronostico)
    return {
        "fecha": pronostico.fecha,
        "pronostico": {
            "viento_superficie_kmh": pronostico.viento_superficie_kmh,
            "rafagas_kmh": pronostico.rafagas_kmh,
            "precipitacion_mm": pronostico.precipitacion_mm,
            "nubosidad_pct": pronostico.nubosidad_pct,
            "temperatura_max_c": pronostico.temperatura_max_c,
        },
        "nivel": evaluacion.nivel,
        "motivos": list(evaluacion.motivos),
    }


def agendar_cita(
    nombre: str,
    fecha_iso: str,
    hora: str,
    servicio: str,
    confirmar_marginal: bool = False,
    descargar: Callable[[date], dict] = _descargar_pronostico,
    archivo: Path = ARCHIVO_CITAS,
) -> dict:
    """Agenda una cita sólo si el clima del día lo permite. Se consulta el clima antes de guardar."""
    if not PATRON_HORA.match(hora):
        raise ValueError(f"La hora '{hora}' debe tener formato HH:MM (24 horas).")

    fecha = validar_fecha(fecha_iso)
    pronostico = obtener_pronostico(fecha, descargar)
    evaluacion = evaluar(pronostico)

    if evaluacion.nivel == PROHIBIDO or (not evaluacion.permite_agendar and not confirmar_marginal):
        return {
            "agendada": False,
            "nivel": evaluacion.nivel,
            "motivos": list(evaluacion.motivos),
            "mensaje": "El clima de ese día no permite agendar sin confirmación."
            if evaluacion.nivel != PROHIBIDO
            else "El clima de ese día está prohibido para saltar; se debe elegir otra fecha.",
        }

    cita = {
        "nombre": nombre,
        "fecha": fecha.isoformat(),
        "hora": hora,
        "servicio": servicio,
        "nivel_clima": evaluacion.nivel,
    }
    _guardar_cita(cita, archivo)
    return {"agendada": True, "cita": cita, "motivos": list(evaluacion.motivos)}


def _guardar_cita(cita: dict, archivo: Path) -> None:
    archivo.parent.mkdir(parents=True, exist_ok=True)
    citas = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else []
    citas.append(cita)
    archivo.write_text(json.dumps(citas, ensure_ascii=False, indent=2), encoding="utf-8")


def consultar_faq(consulta: str) -> dict:
    """Busca fichas de FAQ relevantes. Requiere PostgreSQL con pgvector (ver README de HDT4)."""
    from base_datos import buscar_faq

    return {"resultados": buscar_faq(consulta)}
