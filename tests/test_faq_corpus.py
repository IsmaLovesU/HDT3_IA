from pathlib import Path

import pytest

from faq_corpus import parsear_corpus

CORPUS = Path(__file__).resolve().parent.parent / "data" / "Corpus_FAQs_Parachute_SA_2026.txt"


@pytest.fixture(scope="module")
def registros():
    return parsear_corpus(CORPUS)


def test_lee_las_120_fichas(registros):
    assert len(registros) == 120


def test_ids_unicos_y_en_orden(registros):
    ids = [r.id for r in registros]
    assert len(set(ids)) == len(ids)
    assert ids[0] == "FAQ-001" and ids[-1] == "FAQ-120"


def test_seis_categorias(registros):
    assert len({r.categoria for r in registros}) == 6


def test_metadata_es_diccionario(registros):
    assert all(r.metadata["empresa"] == "Parachute S.A." for r in registros)


def test_campos_no_vacios(registros):
    assert all(r.pregunta and r.respuesta for r in registros)


def test_respuesta_con_datos_reales(registros):
    peso = next(r for r in registros if r.id == "FAQ-021")
    assert "100 kg" in peso.respuesta
