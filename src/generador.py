"""
Generador de boletas electricas sinteticas + gold set.

Garantias que da este generador (y que ningun dataset real puede dar)
---------------------------------------------------------------------
1. VERDAD CONOCIDA. Cada valor impreso sale del registro; el registro es el gold set.
2. AUSENCIAS CONTROLADAS. Sabemos exactamente que campos NO estan en cada boleta,
   que es la variable de la que depende todo el hallazgo del proyecto original.
3. COHERENCIA ARITMETICA. neto = suma de cargos, iva = 19% del neto,
   total = neto + iva + exento + saldo anterior. Permite probar reglas de negocio.
4. VARIACION DE LAYOUT. Tres plantillas con distinto orden, distintas etiquetas y
   distinta disposicion, imitando distribuidoras diferentes. Es el escenario que
   rompia al extractor por posicion.

Nada de esto contiene datos de personas o empresas reales.
"""
from __future__ import annotations
import json, random, unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

from esquema import CAMPOS, POR_NOMBRE

IVA = 0.19

DISTRIBUIDORAS = [
    ("LUZANDINA S.A.", "91.111.100-9", "LUZANDINA"),
    ("ELECTRICA DEL VALLE S.A.", "92.222.200-4", "EDELVALLE"),
    ("ENERGIA AUSTRAL S.A.", "93.333.300-К".replace("К", "K"), "AUSTRAL"),
    ("COMPANIA ELECTRICA PACIFICO", "94.444.400-1", "CEPACIFICO"),
    ("DISTRIBUIDORA CORDILLERA", "95.555.500-7", "CORDILLERA"),
]
GIROS = ["COMUNICACIONES", "SERVICIOS SANITARIOS", "INDUSTRIA ALIMENTARIA",
         "COMERCIO AL POR MAYOR", "TRANSPORTE DE CARGA", "MINERIA NO METALICA"]
SUFIJOS = ["S.A.", "SPA", "LTDA.", "S.A."]
RAICES = ["AGUAS DEL SUR", "TEXTIL ANDINA", "FRIGORIFICO PENCO", "TRANSPORTES MAULE",
          "ALIMENTOS QUILLOTA", "CEMENTOS BIOBIO", "PESQUERA ARAUCO", "LACTEOS OSORNO",
          "MADERAS CURICO", "QUIMICA LAMPA", "LOGISTICA RANCAGUA", "ACEROS TALCA"]
COMUNAS = ["PENCO", "QUILLOTA", "OSORNO", "RANCAGUA", "TALCA", "ARAUCO",
           "LAMPA", "CURICO", "VALDIVIA", "ANGOL", "LINARES", "CASABLANCA"]
CALLES = ["AV. LOS CARRERA", "CAMINO A PENCO", "RUTA 5 SUR KM", "AV. ALEMANIA",
          "LOS AROMOS", "PANAMERICANA NORTE KM", "AV. INDUSTRIAL"]
TARIFAS = ["BT1", "BT2", "BT3", "BT4.3", "AT2 PP", "AT4.3", "BT3 PPP", "AT3 PPP"]
SUBESTACIONES = ["ANDALIEN", "DEUCO", "PICARTE", "AYSEN", "LA GREDA", "MAIPO"]
SECTORES = ["SECTOR 1", "SECTOR 2", "SECTOR 3", "SECTOR 4"]


def digito_verificador(cuerpo: int) -> str:
    """Modulo 11 — el RUT chileno lleva digito verificador; generarlo bien es un detalle de dominio."""
    s, m = 0, 2
    for d in reversed(str(cuerpo)):
        s += int(d) * m
        m = 2 if m == 7 else m + 1
    r = 11 - (s % 11)
    return {11: "0", 10: "K"}.get(r, str(r))


def rut_valido(rng: random.Random) -> str:
    cuerpo = rng.randint(60_000_000, 99_999_999)
    return f"{cuerpo:,}".replace(",", ".") + "-" + digito_verificador(cuerpo)


def _sin_tildes(s: str) -> str:
    n = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in n if not unicodedata.combining(c))


def fmt(valor, tipo: str) -> str:
    """Como se IMPRIME un valor en la boleta (formato chileno)."""
    if tipo == "fecha":
        return valor.strftime("%d-%m-%Y")
    if tipo == "int":
        return f"{int(valor):,}".replace(",", ".")
    if tipo == "float":
        return f"{valor:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(valor)


def generar_registro(rng: random.Random, idx: int) -> dict:
    """Construye un registro coherente. Este dict ES el gold set de esa boleta."""
    r: dict = {}
    nombre_d, rut_d, _ = rng.choice(DISTRIBUIDORAS)
    r["distribuidora"] = nombre_d
    r["rut_distribuidora"] = rut_d
    r["tipo_documento"] = rng.choice(["FACTURA ELECTRONICA", "FACTURA ELECTRONICA", "BOLETA ELECTRONICA"])
    r["numero_documento"] = rng.randint(100_000, 9_999_999)
    r["numero_cliente"] = str(rng.randint(100_000, 9_999_999))

    emision = date(2024, 1, 1) + timedelta(days=rng.randint(0, 420))
    r["fecha_emision"] = emision
    r["fecha_vencimiento"] = emision + timedelta(days=rng.choice([14, 15, 20, 25]))

    r["nombre_cliente"] = f"{rng.choice(RAICES)} {rng.choice(SUFIJOS)}"
    r["rut_cliente"] = rut_valido(rng)
    r["comuna"] = rng.choice(COMUNAS)
    r["direccion_suministro"] = f"{rng.choice(CALLES)} {rng.randint(1, 4800)}, {r['comuna']}"
    r["giro"] = rng.choice(GIROS)

    r["tarifa"] = rng.choice(TARIFAS)
    r["potencia_conectada_kw"] = round(rng.uniform(5, 400), 1)
    r["numero_medidor"] = str(rng.randint(1_000_000, 99_999_999))
    r["subestacion"] = rng.choice(SUBESTACIONES)
    r["sector_tarifario"] = rng.choice(SECTORES)

    # consumo coherente: actual = anterior + energia
    r["fecha_lectura_anterior"] = emision - timedelta(days=rng.randint(30, 34))
    r["fecha_lectura_actual"] = emision - timedelta(days=rng.randint(1, 3))
    r["lectura_anterior_kwh"] = rng.randint(100_000, 900_000)
    r["energia_kwh"] = rng.randint(300, 45_000)
    r["lectura_actual_kwh"] = r["lectura_anterior_kwh"] + r["energia_kwh"]
    r["demanda_kw"] = round(rng.uniform(3, 260), 1)
    r["demanda_punta_kw"] = round(r["demanda_kw"] * rng.uniform(0.4, 0.95), 1)

    # cargos coherentes con el consumo
    precio_kwh = rng.uniform(95, 175)
    r["cargo_fijo"] = rng.randint(800, 5_000)
    r["cargo_energia"] = int(r["energia_kwh"] * precio_kwh)
    r["cargo_demanda"] = int(r["demanda_kw"] * rng.uniform(8_000, 16_000))
    r["cargo_servicio_publico"] = rng.randint(900, 60_000)
    r["cargo_estabilizacion"] = rng.randint(1_000, 45_000)
    r["otros_cargos"] = rng.choice([0, rng.randint(-2_000, 9_000)])
    r["interes"] = rng.randint(500, 12_000)
    r["monto_exento"] = rng.randint(1_000, 60_000)
    r["saldo_anterior"] = rng.randint(10_000, 900_000)

    # trampas: existen en el esquema de extraccion, NUNCA en el documento
    for t in ("id_registro", "cuenta_servicio_cencos", "fecha_carga_sistema", "ruta_archivo"):
        r[t] = None

    return r


def aplicar_presencia(r: dict, rng: random.Random) -> dict:
    """Decide que campos APARECEN en esta boleta. Los ausentes quedan en None en el gold set."""
    for c in CAMPOS:
        if c.clase == "trampa":
            r[c.nombre] = None
        elif c.clase == "condicional" and not c.condicion(r):
            r[c.nombre] = None
        elif c.clase == "opcional" and rng.random() > c.p:
            r[c.nombre] = None
    return r


def cerrar_totales(r: dict) -> dict:
    """Aritmetica de la boleta: se calcula DESPUES de saber que cargos existen."""
    cargos = ["cargo_fijo", "cargo_energia", "cargo_demanda", "cargo_servicio_publico",
              "cargo_estabilizacion", "otros_cargos", "interes"]
    r["monto_neto"] = sum(int(r[c]) for c in cargos if r.get(c) is not None)
    r["iva"] = round(r["monto_neto"] * IVA)
    r["total_a_pagar"] = (r["monto_neto"] + r["iva"]
                          + (r["monto_exento"] or 0) + (r["saldo_anterior"] or 0))
    return r


@dataclass
class Plantilla:
    """Cada plantilla imita a una distribuidora: distinto orden, etiquetas y disposicion."""
    codigo: str
    indice_etiqueta: int
    orden: tuple[str, ...]
    dos_columnas: bool
    ruido: bool


PLANTILLAS = (
    Plantilla("A", 0, ("documento", "cliente", "suministro", "consumo", "cargos", "totales"), False, False),
    Plantilla("B", 1, ("totales", "documento", "cliente", "consumo", "cargos", "suministro"), True, True),
    Plantilla("C", 2, ("cliente", "documento", "cargos", "totales", "suministro", "consumo"), False, True),
)

RUIDO = [
    "Si tienes alguna consulta o reclamo puedes contactarnos a traves de nuestros canales.",
    "Contactate con la Superintendencia de Electricidad y Combustibles (SEC).",
    "Revisa el detalle de tu cuenta al reverso de esta pagina.",
    "OPCIONES DE PAGO: sucursales, sitio web y aplicacion movil.",
    "A partir de la fecha de vencimiento se originaran intereses por pago fuera de plazo.",
]


def etiqueta(campo, plantilla: Plantilla) -> str:
    if not campo.etiquetas:
        return campo.nombre
    return campo.etiquetas[plantilla.indice_etiqueta % len(campo.etiquetas)]


def dibujar(r: dict, plantilla: Plantilla, salida: Path) -> None:
    c = rl_canvas.Canvas(str(salida), pagesize=letter)
    W, H = letter
    x0, y = 18 * mm, H - 18 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x0, y, _sin_tildes(r["distribuidora"])); y -= 6 * mm
    c.setFont("Helvetica", 8)
    c.drawString(x0, y, f"R.U.T. {r['rut_distribuidora']}  ·  Giro: Distribucion de Energia Electrica")
    y -= 8 * mm

    if plantilla.ruido:
        c.setFont("Helvetica-Oblique", 7)
        for linea in random.Random(r["numero_documento"]).sample(RUIDO, 2):
            c.drawString(x0, y, _sin_tildes(linea)); y -= 4 * mm
        y -= 3 * mm

    col_x = (x0, x0 + 92 * mm)
    for grupo in plantilla.orden:
        campos = [k for k in CAMPOS if k.grupo == grupo and r.get(k.nombre) is not None]
        if not campos:
            continue
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x0, y, _sin_tildes(grupo.upper())); y -= 1.5 * mm
        c.setLineWidth(0.4); c.line(x0, y, W - 18 * mm, y); y -= 5 * mm

        fila_y = y
        for i, campo in enumerate(campos):
            cx = col_x[i % 2] if plantilla.dos_columnas else x0
            texto = f"{_sin_tildes(etiqueta(campo, plantilla))}: {_sin_tildes(fmt(r[campo.nombre], campo.tipo))}"
            es_total = campo.nombre == "total_a_pagar"
            c.setFont("Helvetica-Bold" if es_total else "Helvetica", 10 if es_total else 8.5)
            c.drawString(cx, fila_y, texto)
            if not plantilla.dos_columnas or i % 2 == 1:
                fila_y -= 5 * mm
        if plantilla.dos_columnas and len(campos) % 2 == 1:
            fila_y -= 5 * mm
        y = fila_y - 4 * mm

        if y < 30 * mm:
            c.showPage(); y = H - 18 * mm

    c.setFont("Helvetica-Oblique", 6.5)
    c.drawString(x0, 12 * mm, "Documento sintetico generado para evaluacion. Datos ficticios.")
    c.save()


def serializar(r: dict) -> dict:
    """Gold set en JSON: fechas como ISO, el resto tal cual."""
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in r.items()}


def generar(n: int, destino_pdf: Path, destino_gold: Path, semilla: int = 7) -> list[dict]:
    rng = random.Random(semilla)
    destino_pdf.mkdir(parents=True, exist_ok=True)
    destino_gold.parent.mkdir(parents=True, exist_ok=True)
    gold = []
    for i in range(n):
        plantilla = PLANTILLAS[i % len(PLANTILLAS)]
        r = cerrar_totales(aplicar_presencia(generar_registro(rng, i), rng))
        nombre = f"boleta_{i:04d}_{plantilla.codigo}.pdf"
        dibujar(r, plantilla, destino_pdf / nombre)
        fila = serializar(r)
        fila["_archivo"] = nombre
        fila["_plantilla"] = plantilla.codigo
        gold.append(fila)
    destino_gold.write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")
    return gold
