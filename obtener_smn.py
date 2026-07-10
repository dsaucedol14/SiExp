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

    # Ordena por fecha y hora
    reg.sort(key=lambda r: (str(r.get("dloc", "")), int(r.get("hloc", 0))))

    salida = json.dumps(reg, ensure_ascii=False, indent=2)
    with open("noche_smn.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False))

    print(f"{len(reg)} registros de {MUNICIPIO} guardados en noche_smn.json\n")
    print(salida)


if __name__ == "__main__":
    main()
