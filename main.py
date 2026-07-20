"""
main.py
-------
Sistema experto de alerta temprana de heladas radiativas para produccion
de manzana en la Sierra Norte de Puebla (prueba de concepto).

Orquesta: adaptador SMN  ->  motor de inferencia (factores de certeza)
          ->  clasificacion  ->  traza de explicacion.

Uso:
    python main.py                    (descarga en vivo del SMN, genera reporte_heladas.html)
    python main.py --fuente archivo --datos noche_helada.json --parte-baja
    python main.py --fuente api --idmun 21071        (deshabilitado en la PoC)
    python main.py --sin-html                        (omite la generacion del HTML)
"""

import argparse

from motor_cf import MotorInferencia, clasificar
from base_conocimiento import REGLAS
import adaptador_smn as smn


def explicar(cf: float, disparadas: list) -> str:
    """Construye la justificacion legible de la inferencia (la traza)."""
    a_favor = [r for r in disparadas if r.cf > 0]
    en_contra = [r for r in disparadas if r.cf < 0]
    lineas = []
    for r in a_favor:
        lineas.append(f"      ({r.cf:+.2f}) {r.id}: {r.descripcion}")
    for r in en_contra:
        lineas.append(f"      ({r.cf:+.2f}) {r.id}: {r.descripcion}")
    return "\n".join(lineas) if lineas else "      (ninguna regla se disparo)"


def procesar_noche(hechos_por_hora: list) -> list:
    """Corre el motor hora por hora y devuelve los resultados."""
    motor = MotorInferencia(REGLAS)
    resultados = []
    for h in hechos_por_hora:
        cf, disparadas = motor.inferir(h)
        nivel, accion = clasificar(cf)
        resultados.append({
            "hechos": h, "cf": cf, "nivel": nivel,
            "accion": accion, "disparadas": disparadas,
        })
    return resultados


def imprimir_reporte(resultados: list):
    print("\n" + "=" * 70)
    print(" SISTEMA EXPERTO DE ALERTA DE HELADAS - Sierra Norte de Puebla")
    print(" Manzana | Metodo: factores de certeza (MYCIN)")
    print("=" * 70)

    # --- Linea de tiempo horaria ---
    print("\n Evolucion del riesgo durante la noche:\n")
    print(f" {'Fecha':>8} | {'Hora':>4} | {'T':>5} | {'Td':>5} | {'Nub%':>4} | "
          f"{'Vnto':>4} | {'CF':>6} | Nivel")
    print(" " + "-" * 73)
    for r in resultados:
        h = r["hechos"]
        print(f" {smn.fecha_corta(h.get('fecha','')):>8} | {h['hora']:>02}:00 | "
              f"{h['temp']:>5.1f} | {h['td']:>5.1f} | "
              f"{h['nubosidad']:>4.0f} | {h['viento']:>4.0f} | "
              f"{r['cf']:>+6.2f} | {r['nivel']}")

    # --- Momento de mayor riesgo ---
    pico = max(resultados, key=lambda r: r["cf"])
    hp = pico["hechos"]
    print("\n" + "-" * 70)
    print(f" DICTAMEN DE LA NOCHE: {pico['nivel']}  (CF = {pico['cf']:+.2f})")
    print(f" Momento de mayor riesgo: {smn.fecha_corta(hp.get('fecha',''))} "
          f"{hp['hora']:02d}:00 h")
    print(f" Accion recomendada: {pico['accion']}")
    print("\n Justificacion de la inferencia (regla por regla):")
    print(explicar(pico["cf"], pico["disparadas"]))
    print("\n Lectura fisica:")
    print(f"   El punto de rocio estimado es {hp['td']:.1f} C con nubosidad "
          f"del {hp['nubosidad']:.0f}% y viento de {hp['viento']:.0f} km/h.")
    if hp["td"] <= 0 and hp["nubosidad"] <= 25 and hp["viento"] <= 5:
        print("   En noche despejada y en calma, la minima nocturna tiende")
        print("   al punto de rocio: se espera temperatura bajo cero.")
    print("=" * 70 + "\n")


def main():
    ap = argparse.ArgumentParser(
        description="Sistema experto de heladas (PoC) - factores de certeza")
    ap.add_argument("--fuente", choices=["smn", "archivo", "api"], default="smn",
                    help="origen de los datos meteorologicos "
                         "(smn = descarga en vivo del SMN, por defecto)")
    ap.add_argument("--datos", default="noche_helada.json",
                    help="ruta del JSON del SMN cacheado (fuente=archivo)")
    ap.add_argument("--idmun", default=None,
                    help="clave de municipio del SMN (fuente=api)")
    ap.add_argument("--parte-baja", action="store_true",
                    help="el huerto esta en zona de drenaje de aire frio (R9)")
    ap.add_argument("--html", nargs="?", const="reporte_heladas.html",
                    default="reporte_heladas.html",
                    help="ruta de salida del reporte HTML, que se genera "
                         "siempre (por defecto: reporte_heladas.html); "
                         "usa --sin-html para omitirlo")
    ap.add_argument("--sin-html", action="store_true",
                    help="no genera el reporte HTML")
    args = ap.parse_args()

    try:
        if args.fuente == "smn":
            hechos = smn.cargar_desde_smn(args.parte_baja)
        elif args.fuente == "archivo":
            hechos = smn.cargar_desde_archivo(args.datos, args.parte_baja)
        else:
            hechos = smn.cargar_desde_api(args.idmun, args.parte_baja)
    except FileNotFoundError:
        print(f"No se encontro el archivo de datos: {args.datos}")
        return
    except NotImplementedError as e:
        print(f"\n[Aviso] {e}\n")
        return
    except RuntimeError as e:
        print(f"\n[Error al descargar datos del SMN] {e}\n")
        return
    except Exception as e:
        print(f"\n[Error al descargar datos del SMN] {e}\n"
              "Revisa tu conexion o usa --fuente archivo con un JSON cacheado.\n")
        return

    if not hechos:
        print("No se obtuvieron registros meteorologicos.")
        return

    resultados = procesar_noche(hechos)
    imprimir_reporte(resultados)

    if args.html and not args.sin_html:
        import reporte_html
        fechas = [h["fecha"] for h in hechos if h.get("fecha")]
        if fechas:
            f_ini, f_fin = fechas[0], fechas[-1]
            fecha_meta = (smn.fecha_larga(f_ini) if f_ini == f_fin else
                          f"{smn.fecha_larga(f_ini)} al {smn.fecha_larga(f_fin)}")
        else:
            fecha_meta = ""
        meta = {
            "municipio": "Huauchinango, Puebla",
            "fecha": fecha_meta,
            "parte_baja": args.parte_baja,
        }
        ruta = reporte_html.generar_reporte(resultados, meta, args.html, explicar)
        print(f" Reporte HTML generado: {ruta}")
        print(" Abrelo en tu navegador (doble clic o arrastralo a una pestana).\n")


if __name__ == "__main__":
    main()
