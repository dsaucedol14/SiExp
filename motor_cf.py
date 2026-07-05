"""
motor_cf.py
-----------
Motor de inferencia por factores de certeza (estilo MYCIN).

Este módulo NO sabe nada de heladas ni de meteorología: solo sabe
combinar factores de certeza y disparar reglas sobre un diccionario
de hechos. Esa separación entre MOTOR y BASE DE CONOCIMIENTO es lo que
distingue un sistema experto de un simple bloque de if/else.
"""

from dataclasses import dataclass
from typing import Callable, List, Tuple


# ---------------------------------------------------------------------------
# Combinación de factores de certeza (fórmulas clásicas de MYCIN)
# ---------------------------------------------------------------------------
def combinar_cf(cf1: float, cf2: float) -> float:
    """Combina dos factores de certeza sobre la MISMA hipótesis."""
    if cf1 >= 0 and cf2 >= 0:
        return cf1 + cf2 * (1 - cf1)
    if cf1 < 0 and cf2 < 0:
        return cf1 + cf2 * (1 + cf1)
    # signos opuestos
    return (cf1 + cf2) / (1 - min(abs(cf1), abs(cf2)))


def combinar_lista(cfs: List[float]) -> float:
    """Acumula una lista de CF aplicando combinar_cf dos a dos."""
    if not cfs:
        return 0.0
    acumulado = cfs[0]
    for cf in cfs[1:]:
        acumulado = combinar_cf(acumulado, cf)
    # se acota por seguridad numérica
    return max(-1.0, min(1.0, acumulado))


# ---------------------------------------------------------------------------
# Representación de una regla
# ---------------------------------------------------------------------------
@dataclass
class Regla:
    id: str
    descripcion: str
    condicion: Callable[[dict], bool]   # función sobre los hechos
    cf: float                           # factor de certeza de la regla

    def se_dispara(self, hechos: dict) -> bool:
        return bool(self.condicion(hechos))


# ---------------------------------------------------------------------------
# Motor de inferencia (encadenamiento hacia adelante)
# ---------------------------------------------------------------------------
class MotorInferencia:
    def __init__(self, reglas: List[Regla]):
        self.reglas = reglas

    def inferir(self, hechos: dict) -> Tuple[float, List[Regla]]:
        """
        Evalúa todas las reglas contra los hechos, combina los CF de las
        que se disparan y devuelve (cf_final, reglas_disparadas).
        """
        disparadas = [r for r in self.reglas if r.se_dispara(hechos)]
        cf_final = combinar_lista([r.cf for r in disparadas])
        return cf_final, disparadas


# ---------------------------------------------------------------------------
# Mapeo de CF final a nivel de alerta y acción
# ---------------------------------------------------------------------------
def clasificar(cf: float) -> Tuple[str, str]:
    """Devuelve (nivel, accion_recomendada) a partir del CF final."""
    if cf >= 0.70:
        return ("CRITICA",
                "Activar riego por aspersion / calentadores y alarma nocturna")
    if cf >= 0.40:
        return ("ALERTA",
                "Preparar medidas de proteccion y monitoreo continuo")
    if cf >= 0.15:
        return ("VIGILANCIA",
                "Observar evolucion hacia la madrugada")
    return ("NULO", "Sin riesgo relevante de helada radiativa")
