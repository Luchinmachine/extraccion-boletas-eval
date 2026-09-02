"""
Paso 02 — auto-test del generador.

Antes de medir a ningun modelo hay que probar el instrumento. Dos comprobaciones:

  A. TODO valor que el gold declara presente aparece impreso en el PDF.
     Si falla, el gold miente y cualquier metrica posterior es basura.
  B. La aritmetica cierra: neto = suma de cargos, iva = 19% del neto,
     total = neto + iva + exento + saldo anterior.

Es la leccion que ya nos costo tres veces en este proyecto: el instrumento
con el que mides tambien se mide.
"""
import json, sys, unicodedata, re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
from esquema import CAMPOS, POR_NOMBRE                 # noqa: E402
from generador import fmt, IVA                         # noqa: E402
from ingesta import cargar_corpus                      # noqa: E402
from datetime import date                              # noqa: E402


def norm(s) -> str:
    n = unicodedata.normalize("NFKD", str(s))
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[\s.,\-_/]", "", n.lower())


def main() -> None:
    gold = json.loads((RAIZ / "data/gold/gold.json").read_text(encoding="utf-8"))
    textos = cargar_corpus(RAIZ / "data/sinteticas")
    print("=" * 66); print("PASO 02 — AUTO-TEST DEL GENERADOR"); print("=" * 66)
    print(f"PDFs leidos: {len(textos)} · registros en gold: {len(gold)}")

    fallos_a, fallos_b, revisadas = [], [], 0
    for g in gold:
        t = norm(textos[g["_archivo"]])
        for c in CAMPOS:
            v = g[c.nombre]
            if v is None or c.clase == "trampa":
                continue
            revisadas += 1
            valor = date.fromisoformat(v) if c.tipo == "fecha" else v
            if norm(fmt(valor, c.tipo)) not in t:
                fallos_a.append((g["_archivo"], c.nombre, fmt(valor, c.tipo)))

        cargos = ["cargo_fijo", "cargo_energia", "cargo_demanda", "cargo_servicio_publico",
                  "cargo_estabilizacion", "otros_cargos", "interes"]
        neto = sum(int(g[c]) for c in cargos if g.get(c) is not None)
        total = neto + round(neto * IVA) + (g["monto_exento"] or 0) + (g["saldo_anterior"] or 0)
        if neto != g["monto_neto"] or total != g["total_a_pagar"]:
            fallos_b.append(g["_archivo"])

    print(f"\nA. Valores presentes que aparecen impresos : {revisadas - len(fallos_a)}/{revisadas}")
    if fallos_a:
        print(f"   FALLOS: {len(fallos_a)}")
        for f in fallos_a[:8]:
            print(f"     {f[0]}  {f[1]} = {f[2]}")
    print(f"B. Boletas con aritmetica coherente        : {len(gold)-len(fallos_b)}/{len(gold)}")
    if fallos_b:
        print(f"   FALLOS: {fallos_b[:5]}")

    ok = not fallos_a and not fallos_b
    print("\n" + ("GENERADOR VALIDADO — el gold set es confiable."
                  if ok else "HAY FALLOS: corregir antes de medir nada."))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
