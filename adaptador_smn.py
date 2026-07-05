"""
adaptador_smn.py
----------------
Adaptador que traduce el JSON del web service del SMN (CONAGUA) a los
hechos internos que consume la base de conocimiento, y calcula el punto
de rocio.

Por que un adaptador: los nombres de campo cambian entre el pronostico
DIARIO y el POR HORA del SMN, y su esquema puede cambiar en el tiempo.
Si aislamos esa traduccion aqui, las reglas nunca se enteran: si el SMN
cambia, solo se toca este archivo.

Fuentes de datos del SMN:
  - Pronostico por municipios POR HORA (48 h), JSON, actualizado c/1h15m
  - Pronostico por municipios POR DIA (3 dias), JSON
  Endpoint base: https://smn.conagua.gob.mx/  (ver README para la ruta vigente)

NOTA IMPORTANTE: verifica el nombre exacto de cada campo con tu primera
descarga real. Aqui se mapean los nombres tipicos; si alguno difiere,
ajusta solo el diccionario MAPEO_CAMPOS.
"""

import json
import math

# Nombres tipicos de campo en el JSON del SMN -> nombre interno.
# Ajusta la parte derecha si tu descarga real usa otras claves.
MAPEO_CAMPOS = {
    "temp": "temp",        # temperatura del aire (C)
    "hr": "hr",            # humedad relativa (%)
    "velvien": "viento",   # velocidad del viento (km/h)
    "cc": "nubosidad",     # cobertura de nubes (%)
    "hloc": "hora",        # hora local (hh)
}


def punto_de_rocio(temp: float, hr: float) -> float:
    """
    Punto de rocio por la formula de Magnus.
    temp en C, hr en %. Devuelve Td en C.
    """
    hr = max(1.0, min(100.0, hr))  # evita log(0)
    gamma = math.log(hr / 100.0) + (17.27 * temp) / (237.7 + temp)
    return (237.7 * gamma) / (17.27 - gamma)


def _num(valor, defecto=0.0) -> float:
    """Convierte a float de forma tolerante (el SMN a veces manda strings)."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return defecto


def normalizar_registro(reg_smn: dict, parte_baja: bool = False) -> dict:
    """
    Toma un registro horario crudo del SMN y produce el diccionario de
    hechos interno, incluyendo el punto de rocio derivado.
    """
    hechos = {}
    for campo_smn, campo_interno in MAPEO_CAMPOS.items():
        hechos[campo_interno] = _num(reg_smn.get(campo_smn))

    hechos["hora"] = int(hechos["hora"])
    hechos["td"] = round(punto_de_rocio(hechos["temp"], hechos["hr"]), 1)
    hechos["parte_baja"] = parte_baja
    return hechos


def cargar_desde_archivo(ruta: str, parte_baja: bool = False) -> list:
    """
    Lee un JSON del SMN cacheado en disco (lista de registros horarios)
    y devuelve la lista de hechos normalizados, uno por hora.
    """
    with open(ruta, "r", encoding="utf-8") as f:
        crudo = json.load(f)

    # El SMN suele devolver una lista de registros horarios.
    registros = crudo if isinstance(crudo, list) else crudo.get("data", [])
    return [normalizar_registro(r, parte_baja) for r in registros]


def cargar_desde_api(idmun: str, parte_baja: bool = False) -> list:
    """
    Descarga en vivo del web service del SMN. Se deja como stub para la
    PoC: para la demo se recomienda la ruta 'archivo' (mas robusta).

    Para activarla, descomenta y ajusta la URL vigente del SMN a la ruta
    del pronostico POR HORA por municipio, e instala 'requests'.
    """
    raise NotImplementedError(
        "Descarga en vivo deshabilitada en la PoC. "
        "Usa --fuente archivo con un JSON cacheado del SMN. "
        "Ver README para habilitar la ruta API."
    )
