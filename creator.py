import csv
from pathlib import Path

SUBFOLDERS = ["Documentos Gubernamentales", "Transcripciones Entrevistas"]

RESERVED_NAMES = {
    "CON","PRN","AUX","NUL",
    *{f"COM{i}" for i in range(1,10)},
    *{f"LPT{i}" for i in range(1,10)},
}

def sanitize_name(name: str) -> str:
    name = name.strip()
    invalid = '<>:"/\\|?*'
    name = "".join(c for c in name if c not in invalid)
    name = name.rstrip(". ")
    if name.upper() in RESERVED_NAMES:
        name += "_"
    return name

def is_header(value: str) -> bool:
    v = value.strip().lower()
    return any(k in v for k in ("partido", "candidato", "presidencial", "nombre"))

def leer_primer_columna(csv_path: Path) -> list[str]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        except Exception:
            dialect = csv.excel
        reader = csv.reader(f, dialect)
        nombres = []
        primera = True
        for row in reader:
            if not row:
                continue
            valor = row[0].strip()
            if not valor:
                continue
            if primera and is_header(valor):
                primera = False
                continue
            primera = False
            nombres.append(valor)
        return nombres

def main():
    base_dir = Path(__file__).resolve().parent
    csv_path = base_dir / "candidatos presidenciales.csv"
    if not csv_path.exists():
        print(f"No se encontró: {csv_path}")
        return

    partidos_raw = leer_primer_columna(csv_path)
    vistos = set()
    partidos = []
    for p in partidos_raw:
        s = sanitize_name(p)
        if not s:
            continue
        key = s.lower()
        if key in vistos:
            continue
        vistos.add(key)
        partidos.append(s)

    if not partidos:
        print("No se encontraron partidos en la primera columna.")
        return

    for partido in partidos:
        partido_dir = base_dir / partido
        partido_dir.mkdir(parents=True, exist_ok=True)
        for sub in SUBFOLDERS:
            (partido_dir / sub).mkdir(parents=True, exist_ok=True)

    print(f"Carpetas creadas para {len(partidos)} partido(s) en {base_dir}")

if __name__ == "__main__":
    main()