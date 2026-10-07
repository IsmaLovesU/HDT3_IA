"""Herramientas del SDK de OpenAI Agents que usan las tres arquitecturas.

Cada función envuelve una integración de `integraciones.py`. Los errores de validación
(fecha fuera de rango, formato inválido) se devuelven como JSON para que el agente
pueda corregir al usuario en vez de romper la ejecución.
"""

import json

from agents import function_tool

from herramientas import integraciones


def _resultado(funcion, **kwargs) -> str:
    try:
        return json.dumps(funcion(**kwargs), ensure_ascii=False)
    except ValueError as error:
        return json.dumps({"error": str(error)}, ensure_ascii=False)


@function_tool
def consultar_faq(consulta: str) -> str:
    """Busca en la base de FAQs del evento. Úsala para cualquier pregunta informativa."""
    return _resultado(integraciones.consultar_faq, consulta=consulta)


@function_tool
def consultar_clima(fecha: str) -> str:
    """Consulta el pronóstico de Open-Meteo para el lugar de aterrizaje en una fecha (AAAA-MM-DD).
    Devuelve el nivel del día (ideal, marginal o prohibido) y los motivos. Sólo hay pronóstico hasta 16 días."""
    return _resultado(integraciones.consultar_clima, fecha_iso=fecha)


@function_tool
def agendar_cita(
    nombre: str,
    fecha: str,
    hora: str,
    servicio: str,
    confirmar_marginal: bool = False,
) -> str:
    """Agenda una cita para saltar. Revisa el clima antes: un día prohibido nunca se agenda.
    Un día marginal sólo se agenda si confirmar_marginal es true (el usuario lo aceptó).
    fecha es AAAA-MM-DD y hora es HH:MM en 24 horas."""
    return _resultado(
        integraciones.agendar_cita,
        nombre=nombre,
        fecha_iso=fecha,
        hora=hora,
        servicio=servicio,
        confirmar_marginal=confirmar_marginal,
    )
