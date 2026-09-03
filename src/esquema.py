"""
Esquema de la boleta electrica y GENERADOR DE VERDAD (ground truth).

Idea central del proyecto
-------------------------
En el proyecto original no habia forma de saber si el extractor acertaba: no
existia una hoja de respuestas. Aqui invertimos el problema: como NOSOTROS
generamos la boleta, conocemos cada valor por construccion. El gold set sale
gratis y es perfecto.

Eso permite medir lo que antes no se podia:
  - aciertos reales (accuracy por campo),
  - y sobre todo el reparto de los ERRORES en cuatro casos, no dos.

Las cuatro clases de campo (esta es la decision de diseno importante)
---------------------------------------------------------------------
SIEMPRE      El dato aparece en toda boleta. Si el modelo lo deja vacio, es un
             'miss' (lo que le pasaba al extractor por plantillas).
CONDICIONAL  El dato aparece solo si se cumple una regla del dominio. Ejemplo:
             una tarifa BT1 (residencial/pequena) NO factura potencia, asi que
             demanda_kw no existe en esa boleta. Un modelo que la inventa esta
             ignorando el dominio electrico.
OPCIONAL     Aparece con cierta probabilidad (saldo anterior, intereses...).
             Es el terreno natural del relleno: a veces esta, a veces no.
TRAMPA       NUNCA aparece en NINGUNA boleta. Son campos que en el proyecto real
             venian de la base de datos de la plataforma (id, cuenta contable,
             fecha de carga, ruta del archivo) y que alguien copio al esquema de
             extraccion por error.

             >>> La TRAMPA es la sonda mas limpia del proyecto: cualquier valor
             no nulo en estos campos es, por construccion, una alucinacion.
             No hace falta interpretar nada. Tasa de alucinacion pura.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional

Clase = Literal["siempre", "condicional", "opcional", "trampa"]
Tipo = Literal["str", "int", "float", "fecha"]


@dataclass(frozen=True)
class Campo:
    nombre: str
    tipo: Tipo
    clase: Clase
    grupo: str
    descripcion: str
    #: etiqueta con la que el dato aparece impreso, por plantilla
    etiquetas: tuple[str, ...] = ()
    #: para 'condicional': regla sobre el registro ya construido
    condicion: Optional[Callable[[dict], bool]] = None
    #: para 'opcional': probabilidad de aparecer
    p: float = 1.0


def _no_es_bt1(r: dict) -> bool:
    """Las tarifas BT1 no facturan potencia: no llevan demanda ni cargo por demanda."""
    return not str(r.get("tarifa", "")).upper().startswith("BT1")


def _tiene_punta(r: dict) -> bool:
    """Solo las tarifas 'presente en punta' (PP/PPP) facturan demanda de punta."""
    return "PP" in str(r.get("tarifa", "")).upper()


CAMPOS: tuple[Campo, ...] = (
    # ── identificacion del documento ─────────────────────────────────────────
    Campo("distribuidora", "str", "siempre", "documento",
          "Nombre de la empresa distribuidora que emite la boleta.",
          ("Distribuidora", "Empresa")),
    Campo("rut_distribuidora", "str", "siempre", "documento",
          "RUT de la empresa distribuidora, formato chileno.",
          ("R.U.T.", "RUT Emisor")),
    Campo("tipo_documento", "str", "siempre", "documento",
          "Tipo de documento tributario emitido.",
          ("Tipo de documento", "Documento")),
    Campo("numero_documento", "int", "siempre", "documento",
          "Numero correlativo del documento tributario.",
          ("N°", "Folio", "Nro documento")),
    Campo("numero_cliente", "str", "siempre", "documento",
          "Numero identificador del cliente en la distribuidora.",
          ("N° CLIENTE", "Cliente N°", "Rol")),
    Campo("fecha_emision", "fecha", "siempre", "documento",
          "Fecha de emision del documento.",
          ("Fecha de emision", "Emitida el")),
    Campo("fecha_vencimiento", "fecha", "siempre", "documento",
          "Fecha limite de pago sin recargo.",
          ("Fecha de vencimiento", "Vence")),

    # ── cliente ──────────────────────────────────────────────────────────────
    Campo("nombre_cliente", "str", "siempre", "cliente",
          "Razon social del cliente.", ("Sr. (a)", "Cliente")),
    Campo("rut_cliente", "str", "siempre", "cliente",
          "RUT del cliente, formato chileno.", ("RUT", "R.U.T. Cliente")),
    Campo("direccion_suministro", "str", "siempre", "cliente",
          "Direccion donde se presta el servicio electrico.",
          ("Direccion de Suministro", "Domicilio del suministro")),
    Campo("comuna", "str", "siempre", "cliente", "Comuna del suministro.", ("Comuna",)),
    Campo("giro", "str", "opcional", "cliente", "Giro comercial del cliente.", ("Giro",), p=0.7),

    # ── suministro ───────────────────────────────────────────────────────────
    Campo("tarifa", "str", "siempre", "suministro",
          "Tarifa electrica contratada.", ("Tipo de tarifa contratada", "Tarifa")),
    Campo("potencia_conectada_kw", "float", "siempre", "suministro",
          "Potencia conectada, en kW.", ("Potencia conectada", "Pot. conectada")),
    Campo("numero_medidor", "str", "siempre", "suministro",
          "Numero del medidor de energia.", ("N° Medidor", "Medidor")),
    Campo("subestacion", "str", "opcional", "suministro",
          "Subestacion electrica asociada.", ("Subestacion",), p=0.6),
    Campo("sector_tarifario", "str", "opcional", "suministro",
          "Sector tarifario del suministro.", ("Sector tarifario",), p=0.5),

    # ── consumo ──────────────────────────────────────────────────────────────
    Campo("fecha_lectura_anterior", "fecha", "siempre", "consumo",
          "Fecha de la lectura anterior del medidor.", ("Lectura anterior", "Periodo desde")),
    Campo("fecha_lectura_actual", "fecha", "siempre", "consumo",
          "Fecha de la lectura actual del medidor.", ("Lectura actual", "Periodo hasta")),
    Campo("lectura_anterior_kwh", "int", "siempre", "consumo",
          "Valor de la lectura anterior del medidor, en kWh.", ("Lect. anterior",)),
    Campo("lectura_actual_kwh", "int", "siempre", "consumo",
          "Valor de la lectura actual del medidor, en kWh.", ("Lect. actual",)),
    Campo("energia_kwh", "int", "siempre", "consumo",
          "Energia consumida en el periodo, en kWh.", ("Electricidad Consumida", "Consumo")),
    Campo("demanda_kw", "float", "condicional", "consumo",
          "Demanda maxima de potencia leida, en kW.",
          ("Potencia Leida", "Demanda maxima"), condicion=_no_es_bt1),
    Campo("demanda_punta_kw", "float", "condicional", "consumo",
          "Demanda maxima de potencia en horas de punta, en kW.",
          ("Potencia en punta",), condicion=_tiene_punta),

    # ── cargos ───────────────────────────────────────────────────────────────
    Campo("cargo_fijo", "int", "siempre", "cargos",
          "Cargo fijo por administracion del servicio.",
          ("Administracion del Servicio", "Cargo fijo")),
    Campo("cargo_energia", "int", "siempre", "cargos",
          "Cargo por la energia consumida.", ("Electricidad Consumida", "Cargo por energia")),
    Campo("cargo_demanda", "int", "condicional", "cargos",
          "Cargo mensual por demanda maxima de potencia.",
          ("Cargo por demanda", "Cargo por potencia"), condicion=_no_es_bt1),
    Campo("cargo_servicio_publico", "int", "siempre", "cargos",
          "Cargo por servicio publico.", ("Cargo por Servicio Publico",)),
    Campo("cargo_estabilizacion", "int", "opcional", "cargos",
          "Cargo del fondo de estabilizacion tarifaria.",
          ("Cargo Fondo de Estabilizacion",), p=0.6),
    Campo("otros_cargos", "int", "opcional", "cargos",
          "Otros cargos aplicados en el periodo.", ("Otros cargos",), p=0.4),
    Campo("interes", "int", "opcional", "cargos",
          "Intereses por pago fuera de plazo.", ("Intereses",), p=0.15),
    Campo("monto_neto", "int", "siempre", "totales",
          "Monto neto afecto a impuesto.", ("Monto Neto",)),
    Campo("monto_exento", "int", "opcional", "totales",
          "Monto exento de impuesto.", ("Monto Exento",), p=0.5),
    Campo("iva", "int", "siempre", "totales", "Monto del IVA (19%).", ("I.V.A (19%)", "IVA")),
    Campo("saldo_anterior", "int", "opcional", "totales",
          "Saldo pendiente del periodo anterior.", ("Saldo Anterior",), p=0.3),
    Campo("total_a_pagar", "int", "siempre", "totales",
          "Monto total a pagar.", ("TOTAL A PAGAR", "Total del Mes", "MONTO A PAGAR")),

    # ── trampas: nunca impresas en el documento ──────────────────────────────
    Campo("id_registro", "int", "trampa", "sistema",
          "Identificador unico del registro."),
    Campo("cuenta_servicio_cencos", "str", "trampa", "sistema",
          "Cuenta contable de centro de costo asociada al servicio."),
    Campo("fecha_carga_sistema", "fecha", "trampa", "sistema",
          "Fecha y hora en que el registro se cargo al sistema."),
    Campo("ruta_archivo", "str", "trampa", "sistema",
          "Ruta o URL del archivo original de la boleta."),
)

POR_NOMBRE = {c.nombre: c for c in CAMPOS}
TRAMPAS = tuple(c.nombre for c in CAMPOS if c.clase == "trampa")
REALES = tuple(c.nombre for c in CAMPOS if c.clase != "trampa")


def resumen() -> str:
    from collections import Counter
    c = Counter(x.clase for x in CAMPOS)
    return (f"{len(CAMPOS)} campos: {c['siempre']} siempre presentes · "
            f"{c['condicional']} condicionales · {c['opcional']} opcionales · "
            f"{c['trampa']} trampa (nunca en el documento)")


if __name__ == "__main__":
    print(resumen())
    for g in dict.fromkeys(c.grupo for c in CAMPOS):
        print(f"\n[{g}]")
        for c in CAMPOS:
            if c.grupo == g:
                extra = f" p={c.p}" if c.clase == "opcional" else ""
                print(f"  {c.nombre:<26} {c.tipo:<6} {c.clase}{extra}")
