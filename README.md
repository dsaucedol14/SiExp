# Sistema Experto de Alerta de Heladas — Manzana, Sierra Norte de Puebla

Prueba de concepto de un **sistema experto** que estima el riesgo de
**helada radiativa** nocturna en huertos de manzana, usando
**factores de certeza** (paradigma clásico estilo MYCIN).

Consume datos meteorológicos con formato del **web service del SMN
(CONAGUA)** y razona sobre ellos con una base de conocimiento explícita,
separada del motor de inferencia.

## Estructura del proyecto

```
sistema_experto_heladas/
├── motor_cf.py            # Motor de inferencia (combinación de CF, clasificación)
├── base_conocimiento.py   # Las 13 reglas de helada radiativa con sus CF
├── adaptador_smn.py       # Traduce el JSON del SMN + calcula punto de rocío (Magnus)
├── main.py                # Orquestación, CLI y traza de explicación
├── datos/
│   └── noche_helada.json  # Una noche de heladas (formato tipo SMN) para la demo
└── README.md
```

La separación **motor ↔ base de conocimiento** es intencional: es lo que
distingue un sistema experto de un bloque de `if/else`. El motor no sabe
nada de heladas; la base de conocimiento no sabe nada de cómo se combinan
los factores de certeza.

## Cómo ejecutarlo

Requiere solo Python 3 (sin dependencias externas para la ruta `archivo`).

```bash
# Demo con la noche cacheada, huerto en parte baja (activa la regla R9)
python main.py --fuente archivo --datos datos/noche_helada.json --parte-baja

# Sin la heurística de parte baja
python main.py --fuente archivo --datos datos/noche_helada.json
```

### Reporte HTML (para la defensa)

Agrega `--html` para generar un reporte visual autocontenido (un solo
archivo, con gráficas SVG; no requiere internet ni librerías):

```bash
python main.py --datos datos/noche_helada.json --parte-baja --html reporte_heladas.html
```

Se genera `reporte_heladas.html`; ábrelo con doble clic. Incluye el
veredicto de la noche, la gráfica de temperatura vs. punto de rocío, la
evolución del riesgo por hora, la tabla horaria y la justificación
regla por regla del momento de mayor riesgo.

## Las dos rutas de datos (flag `--fuente`)

| Ruta | Uso | Robustez |
|------|-----|----------|
| `archivo` | Lee un JSON del SMN cacheado en disco | **Recomendada para la demo:** no depende de la red al momento de presentar |
| `api` | Descarga en vivo del SMN | Deshabilitada en la PoC (stub); más vistosa pero frágil |

La estrategia recomendada: hacer **una** descarga real del SMN, guardarla
en `datos/`, y reproducirla como “datos simulados”. Los datos son reales y
verificables, pero la demo nunca falla por el WiFi del salón.

## Sobre el web service del SMN

El SMN (CONAGUA) publica pronóstico por municipios en **JSON**, actualizado
aproximadamente cada hora y 15 minutos:

- **Por hora, a 48 h** — el más útil para este sistema (evolución nocturna)
- **Por día, a 3 días**

Portal del servicio: `https://smn.conagua.gob.mx/` (sección *Web Service /
Pronóstico por municipios*). Verifica la ruta y el formato vigentes al
descargar, y localiza la **clave de municipio (`idmun`) de Huauchinango**
en el catálogo del SMN.

### Importante: verifica los nombres de campo

Los nombres exactos de los campos difieren entre el pronóstico **diario**
y el **por hora**. Este proyecto mapea los nombres típicos en
`adaptador_smn.py` → `MAPEO_CAMPOS`:

| Campo SMN | Interno | Significado |
|-----------|---------|-------------|
| `temp`    | temperatura | °C |
| `hr`      | humedad relativa | % |
| `velvien` | viento | km/h |
| `cc`      | nubosidad | % |
| `hloc`    | hora local | hh |

Si tu descarga real usa otras claves, **solo ajusta ese diccionario**: las
reglas no se enteran.

### NOAA no sirve para este caso

La API pública de NOAA (`api.weather.gov`) solo da pronóstico puntual para
territorio de EE.UU.; no cubre municipios de México. Sus datos globales
(modelo GFS) vienen en GRIB, desproporcionado para una PoC. Por eso aquí
se usa el SMN.

## Cómo razona el sistema (resumen)

1. El **punto de rocío** (derivado con la fórmula de Magnus) es el “piso”
   térmico: en noche despejada y en calma, la mínima nocturna tiende a él.
2. Las condiciones **habilitadoras** (cielo despejado, viento en calma)
   suman evidencia; las **bloqueadoras** (nubes, viento) la restan (CF
   negativo) para evitar falsas alarmas.
3. Los factores de certeza se combinan con las fórmulas de MYCIN y el
   resultado se mapea a un nivel: **NULO / VIGILANCIA / ALERTA / CRÍTICA**.
4. El sistema imprime la **traza de la inferencia** (qué reglas se
   dispararon y con qué CF), que es la justificación legible del dictamen.

## Para la defensa

- La **traza regla por regla** demuestra que es un sistema experto y no un
  clasificador opaco: se puede explicar *por qué* dictaminó cada nivel.
- La **regla R9** (huerto en parte baja / cañada) es conocimiento experto
  **local** que ninguna API contiene: es el valor diferencial del sistema.
- La **línea de tiempo horaria** muestra el riesgo escalando de NULO a
  CRÍTICA conforme el cielo se despeja y el viento amaina.

## Extensiones posibles (fuera del alcance de la PoC)

- Habilitar la ruta `api` real en `adaptador_smn.cargar_desde_api`.
- Añadir un componente de ML ligero que prediga la mínima nocturna y un
  lazo de meta-nivel (MAPE-K) que ajuste los CF según falsos positivos —
  esto ya sería material de tesis, no de PoC.
