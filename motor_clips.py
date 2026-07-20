"""
motor_clips.py
--------------
Motor de inferencia ALTERNATIVO: mismo esquema de factores de certeza
que motor_cf.py, pero el DISPARO de las reglas corre en un motor CLIPS
embebido (via clipspy) en lugar del bucle de Python.

Las condiciones de cada regla se traducen a patrones CLIPS (LHS) sobre
un deftemplate "hecho". Los factores de certeza y la formula de
combinacion MYCIN siguen viviendo en motor_cf.py / base_conocimiento.py,
que son la unica fuente de verdad para esos valores: aqui solo se
reutilizan, para no duplicar numeros en dos lenguajes distintos.
"""

from typing import List, Optional, Tuple

import clips

from motor_cf import Regla, combinar_lista
from base_conocimiento import REGLAS


_DEFTEMPLATES = [
    """(deftemplate hecho
   (slot temp) (slot hr) (slot viento) (slot nubosidad) (slot hora) (slot td)
   (slot parte_baja) (slot mes) (slot delta_t) (slot dir_viento)
   (slot prob_prec) (slot rafaga))""",
    """(deftemplate conclusion (slot id))""",
]

# Cada defrule reproduce la condicion lambda equivalente de
# base_conocimiento.py. El "&:(numberp ?x)" en las reglas extendidas
# (R14, R15, R17, R18, R19) reemplaza al patron "h.get(...) is not None"
# de Python: si el dato no llego (queda como simbolo ND), la regla
# simplemente no se dispara. env.build() solo admite un construct a la
# vez, por eso cada regla es un elemento propio de la lista.
_DEFRULES = [
    """(defrule R1 (hecho (td ?td&:(<= ?td 0)))
   => (assert (conclusion (id R1))))""",
    """(defrule R2 (hecho (td ?td&:(and (> ?td 0) (<= ?td 2))))
   => (assert (conclusion (id R2))))""",
    """(defrule R3 (hecho (td ?td&:(and (> ?td 2) (<= ?td 4))))
   => (assert (conclusion (id R3))))""",
    """(defrule R4 (hecho (nubosidad ?n&:(<= ?n 25)))
   => (assert (conclusion (id R4))))""",
    """(defrule R5 (hecho (viento ?v&:(<= ?v 5)))
   => (assert (conclusion (id R5))))""",
    """(defrule R6 (hecho (hr ?h&:(<= ?h 40)))
   => (assert (conclusion (id R6))))""",
    """(defrule R7 (hecho (hora ?ho&:(member$ ?ho (create$ 18 19 20))) (temp ?t&:(<= ?t 6)))
   => (assert (conclusion (id R7))))""",
    """(defrule R8 (hecho (hora ?ho&:(and (>= ?ho 3) (<= ?ho 7))) (temp ?t&:(<= ?t 4)))
   => (assert (conclusion (id R8))))""",
    """(defrule R9 (hecho (parte_baja TRUE))
   => (assert (conclusion (id R9))))""",
    """(defrule R10 (hecho (nubosidad ?n&:(>= ?n 75)))
   => (assert (conclusion (id R10))))""",
    """(defrule R11 (hecho (viento ?v&:(>= ?v 15)))
   => (assert (conclusion (id R11))))""",
    """(defrule R12 (hecho (temp ?t&:(>= ?t 12)))
   => (assert (conclusion (id R12))))""",
    """(defrule R13 (hecho (td ?td&:(>= ?td 5)))
   => (assert (conclusion (id R13))))""",
    """(defrule R16 (hecho (hora ?ho&:(member$ ?ho (create$ 18 19 20))) (temp ?t) (td ?td&:(<= (- ?t ?td) 2)))
   => (assert (conclusion (id R16))))""",
    """(defrule R20 (hecho (hr ?h&:(>= ?h 90)) (td ?td&:(<= ?td 0)))
   => (assert (conclusion (id R20))))""",
    """(defrule R17 (hecho (mes ?m&:(and (numberp ?m) (member$ ?m (create$ 11 12 1 2)))))
   => (assert (conclusion (id R17))))""",
    """(defrule R18 (hecho (delta_t ?d&:(and (numberp ?d) (<= ?d -2))) (temp ?t&:(<= ?t 6)))
   => (assert (conclusion (id R18))))""",
    """(defrule R19 (hecho (dir_viento ?d&:(and (numberp ?d) (or (>= ?d 315) (<= ?d 45)))))
   => (assert (conclusion (id R19))))""",
    """(defrule R14 (hecho (prob_prec ?p&:(and (numberp ?p) (>= ?p 60))))
   => (assert (conclusion (id R14))))""",
    """(defrule R15 (hecho (rafaga ?r&:(and (numberp ?r) (>= ?r 20))))
   => (assert (conclusion (id R15))))""",
]


def _fmt(valor) -> str:
    """Convierte un valor Python al literal CLIPS equivalente,
    preservando int vs float (member$/eq en CLIPS distinguen el tipo)."""
    if valor is None:
        return "ND"
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, int):
        return str(valor)
    return str(float(valor))


class MotorInferenciaCLIPS:
    """Misma interfaz que MotorInferencia (motor_cf.py): recibe hechos
    por hora y devuelve (cf_final, reglas_disparadas). El disparo de
    reglas corre en un Environment de CLIPS embebido."""

    def __init__(self, reglas: Optional[List[Regla]] = None):
        self.reglas_por_id = {r.id: r for r in (reglas or REGLAS)}
        self.env = clips.Environment()
        for construct in _DEFTEMPLATES:
            self.env.build(construct)
        for regla in _DEFRULES:
            self.env.build(regla)

    def inferir(self, hechos: dict) -> Tuple[float, List[Regla]]:
        self.env.reset()
        hecho_clips = (
            "(hecho "
            f"(temp {_fmt(hechos['temp'])}) "
            f"(hr {_fmt(hechos['hr'])}) "
            f"(viento {_fmt(hechos['viento'])}) "
            f"(nubosidad {_fmt(hechos['nubosidad'])}) "
            f"(hora {_fmt(hechos['hora'])}) "
            f"(td {_fmt(hechos['td'])}) "
            f"(parte_baja {_fmt(hechos.get('parte_baja', False))}) "
            f"(mes {_fmt(hechos.get('mes'))}) "
            f"(delta_t {_fmt(hechos.get('delta_t'))}) "
            f"(dir_viento {_fmt(hechos.get('dir_viento'))}) "
            f"(prob_prec {_fmt(hechos.get('prob_prec'))}) "
            f"(rafaga {_fmt(hechos.get('rafaga'))}))"
        )
        self.env.assert_string(hecho_clips)
        self.env.run()

        disparadas = [
            self.reglas_por_id[str(f["id"])]
            for f in self.env.facts()
            if f.template.name == "conclusion"
        ]
        cf_final = combinar_lista([r.cf for r in disparadas])
        return cf_final, disparadas
