"""
base_conocimiento.py
--------------------
BASE DE CONOCIMIENTO del sistema experto de heladas radiativas para
manzana en la Sierra Norte de Puebla.

Toda la pericia del dominio vive AQUI, separada del motor. Cada regla
concluye sobre la misma hipotesis: HELADA_RADIATIVA_ESTA_NOCHE.

Hechos esperados (diccionario producido por el adaptador del SMN):
    temp        : temperatura del aire (C)
    hr          : humedad relativa (%)
    viento      : velocidad del viento (km/h)
    nubosidad   : cobertura de nubes (%)
    hora        : hora local (0-23)
    td          : punto de rocio derivado (C)     <- calculado por Magnus
    parte_baja  : True si el huerto esta en zona de drenaje de aire frio

Convencion de signos:
    CF positivo  -> evidencia A FAVOR de que habra helada
    CF negativo  -> evidencia EN CONTRA (reglas "bloqueadoras")
"""

from motor_cf import Regla


REGLAS = [
    # --- Evidencia principal: punto de rocio (el "piso" termico nocturno) ---
    Regla("R1", "Punto de rocio <= 0 C (piso termico bajo cero)",
          lambda h: h["td"] <= 0, +0.80),
    Regla("R2", "Punto de rocio entre 0 y +2 C",
          lambda h: 0 < h["td"] <= 2, +0.45),
    Regla("R3", "Punto de rocio entre +2 y +4 C",
          lambda h: 2 < h["td"] <= 4, +0.20),

    # --- Condiciones habilitadoras de la helada radiativa ---
    Regla("R4", "Cielo despejado (nubosidad <= 25%)",
          lambda h: h["nubosidad"] <= 25, +0.70),
    Regla("R5", "Viento en calma (<= 5 km/h)",
          lambda h: h["viento"] <= 5, +0.70),
    Regla("R6", "Aire seco (HR <= 40%)",
          lambda h: h["hr"] <= 40, +0.30),

    # --- Evidencia temporal ---
    Regla("R7", "Atardecer frio (18-20 h y temp <= 6 C)",
          lambda h: h["hora"] in (18, 19, 20) and h["temp"] <= 6, +0.40),
    Regla("R8", "Madrugada critica (03-07 h y temp <= 4 C)",
          lambda h: 3 <= h["hora"] <= 7 and h["temp"] <= 4, +0.55),

    # --- Heuristica local (conocimiento experto regional) ---
    Regla("R9", "Huerto en parte baja / canada (drenaje de aire frio)",
          lambda h: h.get("parte_baja", False), +0.35),

    # --- Reglas bloqueadoras (evitan falsas alarmas) ---
    Regla("R10", "Nubosidad alta (>= 75%): las nubes atrapan la radiacion",
          lambda h: h["nubosidad"] >= 75, -0.65),
    Regla("R11", "Viento moderado/fuerte (>= 15 km/h): mezcla el aire",
          lambda h: h["viento"] >= 15, -0.65),
    Regla("R12", "Atardecer templado (temp >= 12 C)",
          lambda h: h["temp"] >= 12, -0.50),
    Regla("R13", "Punto de rocio alto (>= +5 C)",
          lambda h: h["td"] >= 5, -0.55),

    # ===== Reglas extendidas (R14-R20): aprovechan telemetria adicional =====
    # Usan h.get(...) para no fallar cuando el dato no esta disponible
    # (p. ej. entrada manual); si el hecho falta, la regla no se dispara.

    # --- Nodo A (piso termico): reglas adicionales ---
    Regla("R16", "Margen T-Td <= 2 C al atardecer (18-20 h): fuerte indicador radiativo",
          lambda h: h["hora"] in (18, 19, 20) and (h["temp"] - h["td"]) <= 2, +0.50),
    Regla("R20", "Saturacion con punto de rocio bajo cero (HR >= 90% y Td <= 0)",
          lambda h: h["hr"] >= 90 and h["td"] <= 0, +0.30),

    # --- Nodo C (contexto temporal): reglas adicionales ---
    Regla("R17", "Temporada de heladas (mes nov-feb): factor de fondo",
          lambda h: h.get("mes") in (11, 12, 1, 2), +0.10),
    Regla("R18", "Enfriamiento rapido con aire ya frio (descenso >= 2 C y temp <= 6 C)",
          lambda h: h.get("delta_t") is not None and h["delta_t"] <= -2 and h["temp"] <= 6, +0.40),

    # --- Nodo D (contexto local): advección fria ---
    Regla("R19", "Viento del cuadrante norte (adveccion de aire frio)",
          lambda h: h.get("dir_viento") is not None
                    and (h["dir_viento"] >= 315 or h["dir_viento"] <= 45), +0.25),

    # --- Nodo E (bloqueadores): reglas adicionales ---
    Regla("R14", "Probabilidad de precipitacion alta (>= 60%)",
          lambda h: h.get("prob_prec") is not None and h["prob_prec"] >= 60, -0.55),
    Regla("R15", "Rafagas fuertes (>= 20 km/h): mezcla la capa de aire",
          lambda h: h.get("rafaga") is not None and h["rafaga"] >= 20, -0.45),
]
