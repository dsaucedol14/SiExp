"""
reporte_html.py
---------------
Genera un reporte HTML autocontenido (un solo archivo, sin librerias ni
CDN: las graficas son SVG dibujado por Python) a partir de los resultados
del sistema experto. Pensado para abrir en el navegador durante la defensa.
"""

from html import escape

from adaptador_smn import fecha_corta

# Paleta por nivel de alerta
COLORES = {
    "CRITICA":    "#c0392b",
    "ALERTA":     "#e67e22",
    "VIGILANCIA": "#f1c40f",
    "NULO":       "#27ae60",
}
COLOR_TEXTO_NIVEL = {
    "CRITICA": "#fff", "ALERTA": "#fff", "VIGILANCIA": "#333", "NULO": "#fff",
}


# ---------------------------------------------------------------------------
# Utilidades de dibujo SVG
# ---------------------------------------------------------------------------
def _escala(valor, v_min, v_max, px_min, px_max):
    """Mapea un valor de datos a una coordenada de pixel."""
    if v_max == v_min:
        return (px_min + px_max) / 2
    frac = (valor - v_min) / (v_max - v_min)
    return px_min + frac * (px_max - px_min)


def _fronteras_dia(resultados):
    """Indices donde empieza un dia distinto al anterior (incluye el 0)."""
    fronteras = []
    anterior = None
    for i, r in enumerate(resultados):
        f = r["hechos"].get("fecha", "")
        if f != anterior:
            fronteras.append(i)
            anterior = f
    return fronteras


def _paso_etiquetas(n):
    """Cada cuantos puntos mostrar la etiqueta de hora en el eje X, para
    que no se amontonen cuando el reporte cubre varios dias (muchos
    puntos)."""
    return max(1, -(-n // 24))  # techo(n / 24): como mucho ~24 etiquetas


def _grafica_temperatura(resultados):
    """Linea de temperatura y punto de rocio, con la referencia de 0 C."""
    W, H = 820, 300
    ml, mr, mt, mb = 55, 20, 20, 45
    x0, x1 = ml, W - mr
    y0, y1 = mt, H - mb

    horas = [r["hechos"]["hora"] for r in resultados]
    temps = [r["hechos"]["temp"] for r in resultados]
    tds = [r["hechos"]["td"] for r in resultados]

    v_min = min(min(temps), min(tds)) - 1
    v_max = max(max(temps), max(tds)) + 1
    n = len(resultados)

    def px(i):
        return _escala(i, 0, n - 1, x0, x1)

    def py(v):
        return _escala(v, v_min, v_max, y1, y0)

    partes = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
              f'style="width:100%;height:auto;font-family:sans-serif">']

    # Rejilla horizontal + etiquetas del eje Y
    paso = 2
    v = int(v_min // paso * paso)
    while v <= v_max:
        y = py(v)
        partes.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" '
                      f'stroke="#eee"/>')
        partes.append(f'<text x="{x0-8}" y="{y+4:.1f}" text-anchor="end" '
                      f'font-size="11" fill="#888">{v}</text>')
        v += paso

    # Banda bajo 0 C (zona de helada)
    if v_min < 0:
        y_cero = py(0)
        partes.append(f'<rect x="{x0}" y="{y_cero:.1f}" width="{x1-x0}" '
                      f'height="{y1-y_cero:.1f}" fill="#c0392b" opacity="0.06"/>')
        partes.append(f'<line x1="{x0}" y1="{y_cero:.1f}" x2="{x1}" '
                      f'y2="{y_cero:.1f}" stroke="#c0392b" stroke-width="1.2" '
                      f'stroke-dasharray="4 3"/>')
        partes.append(f'<text x="{x1-4}" y="{y_cero-5:.1f}" text-anchor="end" '
                      f'font-size="10" fill="#c0392b">0 C</text>')

    # Fronteras de dia: linea vertical + etiqueta de fecha
    fronteras = _fronteras_dia(resultados)
    for i in fronteras:
        x = px(i)
        if i > 0:
            partes.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y1}" '
                          f'stroke="#bbb" stroke-width="1" stroke-dasharray="2 3"/>')
        partes.append(f'<text x="{x:.1f}" y="{H-mb+31}" text-anchor="middle" '
                      f'font-size="10" font-weight="600" fill="#555">'
                      f'{fecha_corta(resultados[i]["hechos"].get("fecha",""))}</text>')

    # Etiquetas del eje X (horas): se omiten cuando coinciden con una
    # etiqueta de fecha para no encimarse, y se espacian si hay muchos dias
    paso_etq = _paso_etiquetas(n)
    for i, h in enumerate(horas):
        if i in fronteras or i % paso_etq != 0:
            continue
        partes.append(f'<text x="{px(i):.1f}" y="{H-mb+18}" '
                      f'text-anchor="middle" font-size="10" fill="#888">'
                      f'{h:02d}</text>')

    # Linea de punto de rocio (punteada)
    pts_td = " ".join(f"{px(i):.1f},{py(tds[i]):.1f}" for i in range(n))
    partes.append(f'<polyline points="{pts_td}" fill="none" stroke="#2980b9" '
                  f'stroke-width="2" stroke-dasharray="5 4"/>')

    # Linea de temperatura (solida)
    pts_t = " ".join(f"{px(i):.1f},{py(temps[i]):.1f}" for i in range(n))
    partes.append(f'<polyline points="{pts_t}" fill="none" stroke="#e67e22" '
                  f'stroke-width="2.5"/>')
    for i in range(n):
        partes.append(f'<circle cx="{px(i):.1f}" cy="{py(temps[i]):.1f}" '
                      f'r="2.5" fill="#e67e22"/>')

    # Leyenda
    partes.append(f'<rect x="{x0+8}" y="{y0+6}" width="14" height="3" '
                  f'fill="#e67e22"/>')
    partes.append(f'<text x="{x0+26}" y="{y0+12}" font-size="11" '
                  f'fill="#555">Temperatura</text>')
    partes.append(f'<line x1="{x0+120}" y1="{y0+8}" x2="{x0+134}" y2="{y0+8}" '
                  f'stroke="#2980b9" stroke-width="2" stroke-dasharray="5 4"/>')
    partes.append(f'<text x="{x0+140}" y="{y0+12}" font-size="11" '
                  f'fill="#555">Punto de rocio</text>')

    partes.append('</svg>')
    return "".join(partes)


def _grafica_riesgo(resultados):
    """Barras del factor de certeza por hora, coloreadas por nivel."""
    W, H = 820, 260
    ml, mr, mt, mb = 55, 20, 20, 45
    x0, x1 = ml, W - mr
    y0, y1 = mt, H - mb

    n = len(resultados)
    horas = [r["hechos"]["hora"] for r in resultados]
    cfs = [r["cf"] for r in resultados]

    def px(i):
        return _escala(i, -0.5, n - 0.5, x0, x1)

    def py(v):
        return _escala(v, -1, 1, y1, y0)

    partes = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
              f'style="width:100%;height:auto;font-family:sans-serif">']

    # Umbrales de nivel
    for umbral, etiqueta in [(0.70, "CRITICA"), (0.40, "ALERTA"),
                             (0.15, "VIGIL."), (0.0, "")]:
        y = py(umbral)
        partes.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" '
                      f'stroke="#ddd" stroke-dasharray="3 3"/>')
        if etiqueta:
            partes.append(f'<text x="{x0-8}" y="{y+4:.1f}" text-anchor="end" '
                          f'font-size="10" fill="#aaa">{umbral:.2f}</text>')

    ancho_barra = (x1 - x0) / n * 0.7
    y_base = py(0)
    fronteras = _fronteras_dia(resultados)
    paso_etq = _paso_etiquetas(n)
    for i, r in enumerate(resultados):
        cf = cfs[i]
        color = COLORES[r["nivel"]]
        y_top = py(max(cf, 0)) if cf >= 0 else y_base
        alto = abs(py(cf) - y_base)
        cx = px(i)
        fecha_tt = fecha_corta(r["hechos"].get("fecha", ""))
        partes.append(f'<rect x="{cx-ancho_barra/2:.1f}" y="{y_top:.1f}" '
                      f'width="{ancho_barra:.1f}" height="{alto:.1f}" '
                      f'fill="{color}" opacity="0.9"><title>'
                      f'{fecha_tt} {horas[i]:02d}:00 CF={cf:+.2f} '
                      f'{r["nivel"]}</title></rect>')
        if i in fronteras:
            if i > 0:
                partes.append(f'<line x1="{cx:.1f}" y1="{y0}" x2="{cx:.1f}" '
                              f'y2="{y1}" stroke="#bbb" stroke-width="1" '
                              f'stroke-dasharray="2 3"/>')
            partes.append(f'<text x="{cx:.1f}" y="{H-mb+31}" '
                          f'text-anchor="middle" font-size="10" '
                          f'font-weight="600" fill="#555">{fecha_tt}</text>')
        elif i % paso_etq == 0:
            partes.append(f'<text x="{cx:.1f}" y="{H-mb+18}" '
                          f'text-anchor="middle" font-size="10" '
                          f'fill="#888">{horas[i]:02d}</text>')

    partes.append(f'<line x1="{x0}" y1="{y_base:.1f}" x2="{x1}" '
                  f'y2="{y_base:.1f}" stroke="#333" stroke-width="1"/>')
    partes.append('</svg>')
    return "".join(partes)


# ---------------------------------------------------------------------------
# Ensamblado del HTML
# ---------------------------------------------------------------------------
def generar_reporte(resultados, meta, ruta_salida, explicar_fn):
    pico = max(resultados, key=lambda r: r["cf"])
    hp = pico["hechos"]
    color_pico = COLORES[pico["nivel"]]
    txt_pico = COLOR_TEXTO_NIVEL[pico["nivel"]]

    # Tabla horaria
    filas = []
    for r in resultados:
        h = r["hechos"]
        c = COLORES[r["nivel"]]
        tc = COLOR_TEXTO_NIVEL[r["nivel"]]
        filas.append(
            f'<tr>'
            f'<td>{fecha_corta(h.get("fecha",""))}</td>'
            f'<td>{h["hora"]:02d}:00</td>'
            f'<td>{h["temp"]:.1f}</td>'
            f'<td>{h["td"]:.1f}</td>'
            f'<td>{h["nubosidad"]:.0f}%</td>'
            f'<td>{h["viento"]:.0f}</td>'
            f'<td>{r["cf"]:+.2f}</td>'
            f'<td style="background:{c};color:{tc};font-weight:600">'
            f'{r["nivel"]}</td>'
            f'</tr>')
    tabla = "\n".join(filas)

    # Justificacion regla por regla
    just_lineas = []
    for r in sorted(pico["disparadas"], key=lambda x: -x.cf):
        signo_color = "#27ae60" if r.cf > 0 else "#c0392b"
        just_lineas.append(
            f'<li><span style="color:{signo_color};font-weight:700;'
            f'font-family:monospace">{r.cf:+.2f}</span> '
            f'<strong>{r.id}</strong> &mdash; {escape(r.descripcion)}</li>')
    justificacion = "\n".join(just_lineas)

    parte_baja_txt = ("Si (zona de drenaje de aire frio)"
                      if meta.get("parte_baja") else "No")
    fecha_meta = meta.get("fecha", "")
    etiqueta_fecha = "Periodo del" if " al " in fecha_meta else "Noche del"
    fecha_pico = fecha_corta(hp.get("fecha", ""))

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alerta de Heladas &mdash; {escape(meta.get('municipio',''))}</title>
<style>
  :root {{ --tinta:#2c3e50; --suave:#7f8c8d; --linea:#ecf0f1; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
          color:var(--tinta); background:#f4f6f8; padding:24px; }}
  .contenedor {{ max-width:900px; margin:0 auto; }}
  header h1 {{ margin:0 0 4px; font-size:22px; }}
  header p {{ margin:0; color:var(--suave); font-size:13px; }}
  .veredicto {{ background:{color_pico}; color:{txt_pico}; border-radius:14px;
                padding:22px 26px; margin:20px 0; display:flex;
                align-items:center; justify-content:space-between;
                flex-wrap:wrap; gap:12px; box-shadow:0 6px 18px rgba(0,0,0,.12); }}
  .veredicto .nivel {{ font-size:30px; font-weight:800; letter-spacing:1px; }}
  .veredicto .cf {{ font-size:14px; opacity:.9; }}
  .veredicto .accion {{ max-width:340px; font-size:14px; line-height:1.4; }}
  .tarjeta {{ background:#fff; border-radius:12px; padding:20px 24px;
              margin:16px 0; box-shadow:0 2px 8px rgba(0,0,0,.05); }}
  .tarjeta h2 {{ margin:0 0 12px; font-size:15px; text-transform:uppercase;
                 letter-spacing:.5px; color:var(--suave); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ padding:7px 10px; text-align:center; border-bottom:1px solid var(--linea); }}
  th {{ color:var(--suave); font-weight:600; text-transform:uppercase;
        font-size:11px; }}
  ul {{ margin:0; padding-left:20px; line-height:1.9; font-size:14px; }}
  .chips {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; }}
  .chip {{ background:var(--linea); border-radius:20px; padding:5px 12px;
           font-size:12px; color:var(--tinta); }}
  footer {{ color:var(--suave); font-size:11px; text-align:center;
            margin-top:24px; line-height:1.6; }}
</style>
</head>
<body>
<div class="contenedor">

  <header>
    <h1>Sistema Experto de Alerta de Heladas Radiativas</h1>
    <p>Produccion de manzana &middot; {escape(meta.get('municipio','Sierra Norte de Puebla'))}
       &middot; {etiqueta_fecha} {escape(fecha_meta)}
       &middot; Metodo: factores de certeza (MYCIN)</p>
  </header>

  <div class="veredicto">
    <div>
      <div class="nivel">{pico['nivel']}</div>
      <div class="cf">CF = {pico['cf']:+.2f} &middot; mayor riesgo el {fecha_pico} a las {hp['hora']:02d}:00 h</div>
    </div>
    <div class="accion"><strong>Accion:</strong> {escape(pico['accion'])}</div>
  </div>

  <div class="tarjeta">
    <h2>Temperatura y punto de rocio durante la noche</h2>
    {_grafica_temperatura(resultados)}
    <p style="font-size:12.5px;color:var(--suave);margin:10px 0 0">
      En noche despejada y en calma, la temperatura minima tiende al punto
      de rocio (linea azul). Cuando este cae bajo 0&nbsp;C, hay riesgo de helada.</p>
  </div>

  <div class="tarjeta">
    <h2>Evolucion del nivel de riesgo (factor de certeza por hora)</h2>
    {_grafica_riesgo(resultados)}
  </div>

  <div class="tarjeta">
    <h2>Detalle horario</h2>
    <table>
      <thead><tr>
        <th>Fecha</th><th>Hora</th><th>T (C)</th><th>Td (C)</th><th>Nubes</th>
        <th>Viento km/h</th><th>CF</th><th>Nivel</th>
      </tr></thead>
      <tbody>
{tabla}
      </tbody>
    </table>
  </div>

  <div class="tarjeta">
    <h2>Justificacion de la inferencia &mdash; momento de mayor riesgo ({fecha_pico} {hp['hora']:02d}:00 h)</h2>
    <ul>
{justificacion}
    </ul>
    <div class="chips">
      <span class="chip">Td estimado: {hp['td']:.1f} C</span>
      <span class="chip">Nubosidad: {hp['nubosidad']:.0f}%</span>
      <span class="chip">Viento: {hp['viento']:.0f} km/h</span>
      <span class="chip">Huerto en parte baja: {parte_baja_txt}</span>
    </div>
  </div>

  <footer>
    Prueba de concepto &middot; Base de conocimiento separada del motor de inferencia.<br>
    Punto de rocio derivado por la formula de Magnus. Datos con formato del
    web service del SMN (CONAGUA).
  </footer>

</div>
</body>
</html>"""

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html)
    return ruta_salida
