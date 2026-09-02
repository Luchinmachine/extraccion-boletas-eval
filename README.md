# Extracción documental con LLMs: ¿mejor, o solo distinta?

Evaluación honesta de un extractor de boletas eléctricas basado en LLM, comparado
contra el extractor por plantillas posicionales al que pretendía reemplazar.

> **Motivación.** Participé en un proyecto real donde se reemplazó un extractor por
> plantillas por uno basado en LLM. Nunca se midió si el reemplazo era mejor. Este
> repositorio responde esa pregunta con datos que puedo publicar.
>
> Los documentos son **sintéticos**: no hay datos de empresas ni personas reales.

## La pregunta

Un extractor por plantillas falla **dejando el campo vacío** — ruidoso, visible, contable.
Un LLM falla **inventando un valor plausible** — silencioso, invisible en una planilla.

Cambiar uno por otro no es automáticamente una mejora: es un intercambio de modos de
falla. Este proyecto mide ese intercambio.

## Por qué datos sintéticos

Generar las boletas resuelve tres problemas de golpe:

1. **Gold set gratis y perfecto.** Conozco cada valor por construcción, para 120
   documentos, sin anotar nada a mano.
2. **Ausencias controladas.** Sé exactamente qué campos *no* están en cada boleta —
   la variable de la que depende todo el fenómeno que se estudia.
3. **Publicable.** Sin datos confidenciales de terceros.

### Campos trampa

El esquema incluye 4 campos que **no aparecen en ninguna boleta** (`id_registro`,
`cuenta_servicio_cencos`, `fecha_carga_sistema`, `ruta_archivo`). En el proyecto real
venían de la base de datos de la plataforma y alguien los copió al esquema de extracción.

Aquí son la sonda más limpia del experimento: **cualquier valor no nulo en esos campos
es, por construcción, una alucinación.** Sin interpretación, sin ambigüedad.

## Estado

| Paso | Descripción | Estado |
|---|---|---|
| 01 | Generador sintético + gold set | ✅ |
| 02 | Auto-test del generador | ✅ |
| 03 | Baseline determinista (tipo plantilla posicional) | ⏳ |
| 04 | Pipeline LLM con salida estructurada | ⏳ |
| 05 | Evaluador de 4 casos | ⏳ |
| 06 | Experimentos de prompt | ⏳ |
| 07 | Umbral de revisión humana | ⏳ |

## Dataset

120 boletas · 40 campos · **3 plantillas de layout** que imitan distribuidoras distintas
(distinto orden de secciones, distintas etiquetas para el mismo dato, una a dos columnas,
con y sin texto de marketing intercalado).

**22,8 % de las celdas del gold set están ausentes** por diseño. Cada una es una
oportunidad de que el modelo rellene en vez de abstenerse.

Las cuatro clases de campo:

| Clase | Qué significa | Qué mide |
|---|---|---|
| `siempre` | Aparece en toda boleta | Si el modelo lo deja vacío, es un *miss* |
| `condicional` | Depende del dominio (una tarifa BT1 no factura potencia) | Si lo inventa, ignora las reglas del negocio |
| `opcional` | Aparece con probabilidad *p* | Terreno natural del relleno |
| `trampa` | Nunca aparece | Alucinación pura |

## Uso

```bash
pip install -r requirements.txt
python scripts/01_generar_dataset.py -n 120
python scripts/02_validar_dataset.py     # debe pasar antes de medir nada
```

El paso 02 comprueba que **todo valor que el gold declara presente aparece impreso en el
PDF** (3.706/3.706) y que la aritmética de cada boleta cierra (120/120). El instrumento
con el que se mide también se mide.
