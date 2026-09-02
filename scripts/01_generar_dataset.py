"""Paso 01 — genera el corpus sintetico y su gold set."""
import argparse, sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
from esquema import CAMPOS, TRAMPAS, resumen          # noqa: E402
from generador import generar, PLANTILLAS             # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=120, help="numero de boletas")
    ap.add_argument("--semilla", type=int, default=7)
    a = ap.parse_args()

    gold = generar(a.n, RAIZ / "data/sinteticas", RAIZ / "data/gold/gold.json", a.semilla)

    print("=" * 66)
    print("PASO 01 — CORPUS SINTETICO Y GOLD SET")
    print("=" * 66)
    print(resumen())
    print(f"\nBoletas generadas : {len(gold)}")
    print(f"Plantillas        : {dict(Counter(g['_plantilla'] for g in gold))}")
    print(f"PDFs              : data/sinteticas/")
    print(f"Gold set          : data/gold/gold.json")

    print("\n--- presencia por campo (cuantas boletas SI traen el dato) ---")
    for c in CAMPOS:
        k = sum(1 for g in gold if g[c.nombre] is not None)
        marca = "  <- TRAMPA: siempre ausente" if c.clase == "trampa" else ""
        print(f"  {c.nombre:<26} {k:>4}/{len(gold)}  ({c.clase}){marca}")

    faltantes = sum(1 for g in gold for c in CAMPOS if g[c.nombre] is None)
    print(f"\nCeldas ausentes en el gold set: {faltantes} de {len(gold)*len(CAMPOS)} "
          f"({faltantes/(len(gold)*len(CAMPOS)):.1%})")
    print("Cada una es una oportunidad de que el modelo rellene en vez de abstenerse.")

    mal = [g["_archivo"] for g in gold if any(g[t] is not None for t in TRAMPAS)]
    print(f"\nControl de integridad — trampas no nulas en el gold: {len(mal)} (debe ser 0)")


if __name__ == "__main__":
    main()
