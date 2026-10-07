from datetime import date, timedelta
from pathlib import Path

import pytest

from herramientas.integraciones import agendar_cita, consultar_clima, validar_fecha
from herramientas.reglas_clima import IDEAL, MARGINAL, PROHIBIDO, Pronostico, evaluar

HOY = date(2026, 10, 6)


def pronostico(**cambios) -> Pronostico:
    base = dict(
        fecha="2026-10-10",
        viento_superficie_kmh=10.0,
        rafagas_kmh=15.0,
        precipitacion_mm=0.0,
        nubosidad_pct=10.0,
        temperatura_max_c=30.0,
    )
    base.update(cambios)
    return Pronostico(**base)


def respuesta_open_meteo(**valores):
    datos = {
        "wind_speed_10m_max": [10.0],
        "wind_gusts_10m_max": [15.0],
        "precipitation_sum": [0.0],
        "cloud_cover_mean": [10.0],
        "temperature_2m_max": [30.0],
    }
    datos.update({k: [v] for k, v in valores.items()})
    return {"daily": datos}


# --- Criterio de seguridad ---------------------------------------------------

def test_dia_ideal():
    assert evaluar(pronostico()).nivel == IDEAL


@pytest.mark.parametrize("viento,nivel", [(19.9, IDEAL), (20.0, MARGINAL), (28.0, MARGINAL), (28.1, PROHIBIDO)])
def test_umbrales_viento_superficie(viento, nivel):
    assert evaluar(pronostico(viento_superficie_kmh=viento)).nivel == nivel


@pytest.mark.parametrize("rafagas,nivel", [(35.0, IDEAL), (35.1, PROHIBIDO)])
def test_umbral_rafagas(rafagas, nivel):
    assert evaluar(pronostico(rafagas_kmh=rafagas)).nivel == nivel


def test_cualquier_lluvia_es_prohibida():
    assert evaluar(pronostico(precipitacion_mm=0.1)).nivel == PROHIBIDO


@pytest.mark.parametrize("nubes,nivel", [(29.9, IDEAL), (30.0, MARGINAL), (75.0, MARGINAL), (75.1, PROHIBIDO)])
def test_umbrales_nubosidad(nubes, nivel):
    assert evaluar(pronostico(nubosidad_pct=nubes)).nivel == nivel


def test_prohibido_gana_sobre_marginal_y_motivos_se_listan():
    evaluacion = evaluar(pronostico(viento_superficie_kmh=22.0, precipitacion_mm=2.0))
    assert evaluacion.nivel == PROHIBIDO
    assert any("precipitación" in m for m in evaluacion.motivos)
    assert any("viento" in m for m in evaluacion.motivos)


def test_solo_ideal_permite_agendar_sin_confirmacion():
    assert evaluar(pronostico()).permite_agendar
    assert not evaluar(pronostico(viento_superficie_kmh=22.0)).permite_agendar


# --- Rango de fechas ---------------------------------------------------------

def test_fecha_dentro_de_16_dias_es_valida():
    assert validar_fecha((HOY + timedelta(days=16)).isoformat(), hoy=HOY) == HOY + timedelta(days=16)


def test_fecha_despues_de_16_dias_se_rechaza_con_correccion():
    with pytest.raises(ValueError, match="16 días"):
        validar_fecha((HOY + timedelta(days=17)).isoformat(), hoy=HOY)


def test_fecha_pasada_se_rechaza():
    with pytest.raises(ValueError, match="ya pasó"):
        validar_fecha((HOY - timedelta(days=1)).isoformat(), hoy=HOY)


def test_formato_de_fecha_invalido():
    with pytest.raises(ValueError, match="AAAA-MM-DD"):
        validar_fecha("10/10/2026", hoy=HOY)


# --- Integración con Open-Meteo (descarga simulada) --------------------------

def test_consultar_clima_no_llama_red_si_la_fecha_esta_fuera_de_rango():
    llamadas = []

    def descargar(fecha):
        llamadas.append(fecha)
        return respuesta_open_meteo()

    fuera = (date.today() + timedelta(days=30)).isoformat()
    with pytest.raises(ValueError):
        consultar_clima(fuera, descargar=descargar)
    assert llamadas == []


def test_consultar_clima_devuelve_nivel_y_valores():
    fecha = (date.today() + timedelta(days=2)).isoformat()
    resultado = consultar_clima(fecha, descargar=lambda f: respuesta_open_meteo(precipitation_sum=1.2))
    assert resultado["nivel"] == PROHIBIDO
    assert resultado["pronostico"]["precipitacion_mm"] == 1.2


def test_agendar_cita_prohibida_no_guarda(tmp_path: Path):
    archivo = tmp_path / "citas.json"
    fecha = (date.today() + timedelta(days=2)).isoformat()
    resultado = agendar_cita(
        "Ana", fecha, "09:00", "tándem",
        descargar=lambda f: respuesta_open_meteo(precipitation_sum=3.0),
        archivo=archivo,
    )
    assert resultado["agendada"] is False and not archivo.exists()


def test_agendar_cita_marginal_requiere_confirmacion(tmp_path: Path):
    archivo = tmp_path / "citas.json"
    fecha = (date.today() + timedelta(days=2)).isoformat()
    marginal = lambda f: respuesta_open_meteo(wind_speed_10m_max=22.0)  # noqa: E731

    sin_confirmar = agendar_cita("Ana", fecha, "09:00", "tándem", descargar=marginal, archivo=archivo)
    assert sin_confirmar["agendada"] is False

    confirmada = agendar_cita("Ana", fecha, "09:00", "tándem", confirmar_marginal=True, descargar=marginal, archivo=archivo)
    assert confirmada["agendada"] is True and archivo.exists()


def test_agendar_cita_ideal_guarda(tmp_path: Path):
    archivo = tmp_path / "citas.json"
    fecha = (date.today() + timedelta(days=2)).isoformat()
    resultado = agendar_cita("Ana", fecha, "09:00", "tándem", descargar=lambda f: respuesta_open_meteo(), archivo=archivo)
    assert resultado["agendada"] is True
    assert resultado["cita"]["nivel_clima"] == IDEAL


def test_hora_invalida_no_consulta_clima(tmp_path: Path):
    llamadas = []
    with pytest.raises(ValueError, match="HH:MM"):
        agendar_cita("Ana", (date.today() + timedelta(days=2)).isoformat(), "25:00", "tándem",
                     descargar=lambda f: llamadas.append(f) or respuesta_open_meteo(), archivo=tmp_path / "c.json")
    assert llamadas == []
