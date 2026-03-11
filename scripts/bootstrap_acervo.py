#!/usr/bin/env python3
"""
Cria uma estrutura inicial de acervo jurídico reutilizável.
"""

import argparse
from pathlib import Path


README_FILES = {
    "README.md": "# ACERVO DE PECAS\n\nEstrutura local para catalogar e reaproveitar pecas do proprio usuario.\n",
    "entrada_novas/README.md": "# ENTRADA NOVAS\n\nColoque aqui arquivos que ainda serao catalogados.\n",
    "catalogadas/README.md": "# CATALOGADAS\n\nArquivos classificados por tipo principal.\n",
    "texto_extraido/README.md": "# TEXTO EXTRAIDO\n\nSaidas em markdown geradas a partir dos arquivos originais.\n",
    "metadados/README.md": "# METADADOS\n\nFichas resumidas por documento catalogado.\n",
    "indices/indice_pecas.md": "# INDICE DE PECAS\n",
    "indices/mapa_tipos.md": "# MAPA DE TIPOS\n",
    "indices/providencias_processos/README.md": "# PROVIDENCIAS PROCESSUAIS\n\nPlanos gerados a partir de processos integrais.\n",
}


def ensure_file(base_dir: Path, relative_path: str, content: str):
    target = base_dir / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Cria a estrutura inicial de acervo_pecas")
    parser.add_argument("--destino", default="acervo_pecas", help="Pasta raiz do acervo")
    args = parser.parse_args()

    base_dir = Path(args.destino)
    directories = [
        base_dir / "entrada_novas",
        base_dir / "texto_extraido",
        base_dir / "catalogadas",
        base_dir / "metadados",
        base_dir / "indices",
        base_dir / "indices" / "providencias_processos",
        base_dir / "tipos",
        base_dir / "referencias",
        base_dir / "scripts",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    for relative_path, content in README_FILES.items():
        ensure_file(base_dir, relative_path, content)

    print(f"OK: estrutura criada em {base_dir.resolve()}")


if __name__ == "__main__":
    main()
