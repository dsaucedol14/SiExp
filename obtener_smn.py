"""
obtener_smn.py
--------------
Descarga el pronóstico por hora del SMN, lo descomprime y extrae solo
los registros de Huauchinango, listos para pegar en la app de heladas
(pestaña "La noche") o para usar con la versión de escritorio.

Uso:
    1. Entra a  https://smn.conagua.gob.mx/es/web-service-api
    2. Copia el enlace del servicio "por municipios POR HORA (48 h)".
    3. Pégalo abajo en la variable URL.
    4. Ejecuta:  python obtener_smn.py
    5. Se crea "noche_smn.json"; abre el archivo, copia su contenido y
       pégalo en la app. (También imprime el resultado en pantalla.)
"""

import urllib.request
import gzip
import json
import io

# --- Pega aquí el enlace del servicio POR HORA que copiaste del SMN ---
URL = "PEGA_AQUI_EL_ENLACE_POR_HORA_DEL_SMN"

# Municipio a extraer (por nombre; no necesitas saber la clave)
MUNICIPIO = "Huauchinango"


def descargar(url):
    """Descarga y descomprime; el SMN entrega JSON en Latin-1 (ISO-8859-1)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    crudo = urllib.request.urlopen(req, timeout=60).read()

    # ¿viene comprimido con gzip? Se detecta por los bytes mágicos 1F 8B
    if crudo[:2] == b"\x1f\x8b":
        crudo = gzip.decompress(crudo)

    # El SMN usa Latin-1, no UTF-8. Probamos UTF-8 y caemos a Latin-1.
    texto = None
    for enc in ("utf-8", "latin-1"):
        try:
            texto = crudo.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        texto = crudo.decode("latin-1", errors="replace")

    texto = texto.strip()

    # Validar que de verdad sea JSON (debe empezar con [ o {)
    if not texto[:1] in "[{":
        raise SystemExit(
            "\n*** El enlace NO devolvió JSON. ***\n"
            "Primeros caracteres de lo que se descargó:\n"
            "---------------------------------------------\n"
            f"{texto[:300]}\n"
            "---------------------------------------------\n"
            "Si ves código HTML (<!DOCTYPE>, <html>...), copiaste la URL de la\n"
            "PÁGINA, no el enlace de descarga. En la página del SMN, haz CLIC\n"
            "DERECHO sobre el enlace del servicio POR HORA y elige 'Copiar\n"
            "dirección del enlace'. Ese es el que va en la variable URL.\n"
        )

    return json.loads(texto)


def nubosidad_desde_cielo(desc):
    """Traduce la descripción textual del cielo del SMN a un % de nubosidad.
    (El servicio por hora no da nubosidad numérica, solo texto en 'desciel'.)"""
    d = str(desc).lower()
    if "cubierto" in d:               return 100
    if "mayormente nublado" in d:     return 80
    if "medio nublado" in d or "parcial" in d:            return 50
    if "intervalos" in d or "dispersas" in d or "poco nublado" in d:  return 30
    if "mayormente despejado" in d:   return 15
    if "nublado" in d:                return 90   # 'nublado' a secas
    if "despejado" in d:              return 5
    return 40   # descripción no reconocida: valor intermedio prudente


def hora_desde_hloc(hloc):
    """Extrae la hora (0-23) de una marca tipo '20260708T18'. Devuelve (fecha, hora)."""
    s = str(hloc)
    if "T" in s:
        fecha, hh = s.split("T", 1)
        try:
            return fecha, int(hh[:2])
        except ValueError:
            return fecha, 0
    # por si viniera solo la hora
    try:
        return "", int(s)
    except ValueError:
        return "", 0


def main():
    if "PEGA_AQUI" in URL:
        print("Falta pegar el enlace del SMN en la variable URL (arriba).")
        return

    data = descargar(URL)
    if not isinstance(data, list):
        data = data.get("data", [])

    # Muestra los campos disponibles del primer registro (por si cambian nombres)
    if data:
        print("Campos que devuelve el SMN:", list(data[0].keys()), "\n")

    # Filtra por nombre de municipio (sin distinguir mayúsculas/acentos básicos)
    obj = MUNICIPIO.strip().lower()
    reg = [r for r in data if str(r.get("nmun", "")).strip().lower() == obj]

    if not reg:
        print(f"No se encontraron registros de '{MUNICIPIO}'.")
        print("Revisa el nombre exacto en el campo 'nmun' de la lista de arriba.")
        return

    # Transforma cada registro del SMN al formato que consume la app:
    #   hloc (hora 0-23), temp, hr, velvien, cc (nubosidad numérica), dloc, td
    convertidos = []
    for r in reg:
        fecha, hora = hora_desde_hloc(r.get("hloc", ""))
        convertidos.append({
            "dloc": fecha,
            "hloc": hora,                                  # hora entera
            "temp": r.get("temp", ""),
            "hr": r.get("hr", ""),
            "velvien": r.get("velvien", ""),
            "cc": nubosidad_desde_cielo(r.get("desciel", "")),  # de texto a %
            "cielo": r.get("desciel", ""),                 # se conserva por claridad
            "dpt": r.get("dpt", ""),                       # punto de rocío del SMN
        })

    # Ordena por fecha y hora
    convertidos.sort(key=lambda r: (str(r["dloc"]), r["hloc"]))

    salida = json.dumps(convertidos, ensure_ascii=False, indent=2)
    with open("noche_smn.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(convertidos, ensure_ascii=False))

    print(f"{len(convertidos)} registros de {MUNICIPIO} guardados en noche_smn.json")
    # Muestra qué descripciones de cielo aparecieron y cómo se tradujeron
    vistos = sorted(set(r["cielo"] for r in convertidos))
    print("Descripciones de cielo encontradas (revisa el mapeo si hace falta):")
    for c in vistos:
        print(f"   '{c}'  ->  nubosidad {nubosidad_desde_cielo(c)} %")
    print()
    print(salida)


if __name__ == "__main__":
    main()
