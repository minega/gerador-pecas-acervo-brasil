#!/usr/bin/env python3
"""
Gera plano de providencias apos decisoes e atos relevantes em processos integrais.

Entrada padrao:
- acervo_pecas/texto_extraido/processo_*.md

Saida padrao:
- acervo_pecas/indices/providencias_processos/providencias_<arquivo>.md
"""

import argparse
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List


MOV_RE = re.compile(
    r"Movimentacao\s+(\d+)\s*:\s*(.+?)(?=\s+Movimentacao\s+\d+\s*:|$)",
    flags=re.IGNORECASE | re.DOTALL,
)

DOC_RE = re.compile(
    r"(Num\.\s*\d{6,}\s*-\s*Pg\.\s*\d+.*?)(?=Num\.\s*\d{6,}\s*-\s*Pg\.\s*\d+|$)",
    flags=re.IGNORECASE | re.DOTALL,
)


@dataclass
class Evento:
    mov: int
    cabecalho: str
    resumo: str
    categoria: str
    providencia: str
    peca_sugerida: str
    alerta: str


def fold_text(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    return folded.encode("ascii", errors="ignore").decode("ascii", errors="ignore").lower()


def clean_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_body(md_text: str) -> str:
    if "## Conteudo" in md_text:
        return md_text.split("## Conteudo", 1)[1].strip()
    return md_text.strip()


def parse_movimentacoes(raw_body: str) -> Dict[int, str]:
    by_mov: Dict[int, str] = {}
    for m in MOV_RE.finditer(raw_body):
        mov = int(m.group(1))
        bloco = clean_spaces(m.group(2))
        if not bloco:
            continue
        # Se o mesmo numero aparece mais de uma vez, preserva o bloco mais completo.
        if mov not in by_mov or len(bloco) > len(by_mov[mov]):
            by_mov[mov] = bloco
    return by_mov


def parse_blocos_documento(raw_body: str) -> Dict[int, str]:
    by_id: Dict[int, str] = {}
    for idx, m in enumerate(DOC_RE.finditer(raw_body), start=1):
        bloco = clean_spaces(m.group(1))
        if not bloco:
            continue
        id_match = re.search(r"Num\.\s*(\d{6,})", bloco, flags=re.IGNORECASE)
        if id_match:
            key = int(id_match.group(1))
        else:
            key = 900000 + idx
        if key not in by_id or len(bloco) > len(by_id[key]):
            by_id[key] = bloco
    return by_id


def extrair_cabecalho(bloco: str) -> str:
    parts = re.split(
        r"\s+(?:Arquivo|Usu[aá]rio|Usurio|Usuario|Processo:)",
        bloco,
        maxsplit=1,
        flags=re.IGNORECASE,
    )
    head = clean_spaces(parts[0]) if parts else clean_spaces(bloco)
    return head[:140]


def classificar_evento(cabecalho: str, bloco: str) -> str:
    h = fold_text(cabecalho)
    p = fold_text(bloco[:260])
    f = fold_text(f"{cabecalho} {bloco[:800]}")

    if any(k in h for k in ("intimacao", "intimao", "intime-se", "intime se")):
        return "intimacao"
    if any(k in h for k in ("citacao", "citao", "cite-se", "cite se")):
        return "citacao"
    if any(k in h for k in ("certidao", "certido")):
        return "certidao"
    if "juntada" in h:
        return "outro"
    if "autos conclusos" in h:
        return "outro"
    if any(k in h for k in ("audiencia", "audincia")):
        return "audiencia"
    if any(k in h for k in ("decisao", "deciso", "despacho", "sentenca", "sentena", "acordao", "liminar", "tutela")):
        return "decisao_judicial"

    # Fallback para extracoes sem cabecalho limpo (ex.: blocos "Num. ...").
    if any(k in p for k in ("audiencia", "audincia")):
        return "audiencia"
    if any(k in p for k in ("citacao", "citao", "pela presente", "fica o(a) executado(a) citado")):
        return "citacao"
    if any(k in p for k in ("intimacao", "intimao", "intime-se", "intime se")):
        return "intimacao"
    if any(k in p for k in ("certidao", "certido", "certifico que")):
        return "certidao"
    if any(k in f for k in ("decisao", "deciso", "despacho", "sentenca", "sentena", "acordao", "liminar", "tutela")):
        return "decisao_judicial"
    return "outro"


def evento_relevante(categoria: str, cabecalho: str, bloco: str) -> bool:
    if categoria in {"decisao_judicial", "audiencia"}:
        return True
    f = fold_text(f"{cabecalho} {bloco[:500]}")
    if categoria == "citacao":
        return any(k in f for k in ("efetivada", "nao efetivada", "no efetivada", "resultado negativo", "expedida"))
    if categoria == "intimacao":
        return any(
            k in f
            for k in (
                "efetivada",
                "prazo",
                "audiencia",
                "referente mov",
                "defer",
                "indefer",
                "sentenca",
                "decisao",
            )
        )
    if categoria == "certidao":
        return any(k in f for k in ("guia", "custas", "audiencia", "prazo", "cumprimento", "determinacao"))
    return any(k in f for k in ("prazo", "dias", "cumprimento", "manifestacao", "determinacao"))


def sugerir_providencia(categoria: str, cabecalho: str, bloco: str):
    f = fold_text(f"{cabecalho} {bloco}")

    if "sentenca" in f:
        return (
            "Analisar resultado e sucumbencia; definir se cabe embargos de declaracao e/ou apelacao.",
            "embargos_declaracao ou apelacao",
            "Conferir data da intimacao efetivada para contagem do prazo recursal.",
        )

    if "acordao" in f:
        return (
            "Analisar colegiado e fundamentos; definir embargos de declaracao e eventual recurso excepcional.",
            "embargos_declaracao / recurso especial / recurso extraordinario",
            "Validar pressupostos de admissibilidade e prazo no tribunal competente.",
        )

    if ("tutela" in f or "liminar" in f) and "indefer" in f:
        return (
            "Preparar ataque imediato da decisao com enfase em probabilidade do direito e perigo de dano.",
            "agravo_instrumento",
            "Prazo recursal depende da intimacao; confirmar no andamento oficial.",
        )

    if ("tutela" in f or "liminar" in f) and any(k in f for k in ("defer", "concess", "defiro")):
        return (
            "Peticionar cumprimento da tutela e, se houver descumprimento, requerer medidas coercitivas.",
            "peticao_cumprimento_tutela",
            "Juntar prova atualizada de cumprimento ou descumprimento.",
        )

    if "emenda inicial" in f or "emendar a inicial" in f:
        return (
            "Adequar a inicial aos pontos exigidos no ato e protocolar emenda completa dentro do prazo.",
            "peticao_emenda_inicial",
            "Conferir itens obrigatorios da emenda e prazo fixado pelo juizo.",
        )

    if categoria == "audiencia":
        return (
            "Preparar estrategia de audiencia e providenciar comparecimento/preposto/procuracao.",
            "peticao_manifestacao_pre_audiencia",
            "Conferir data, plataforma, pauta e requisitos de comparecimento.",
        )

    if categoria == "citacao":
        if "nao efetivada" in f or "no efetivada" in f or "resultado negativo" in f:
            return (
                "Requerer novo meio de citacao com diligencias complementares e enderecos alternativos.",
                "peticao_requerimento_nova_citacao",
                "Anexar pesquisas de endereco para evitar nova frustracao.",
            )
        if "efetivada" in f:
            return (
                "Controlar prazo da resposta da parte contraria e preparar impugnacao/replica.",
                "replica ou impugnacao",
                "Conferir termo inicial de prazo no sistema do tribunal.",
            )
        return (
            "Monitorar retorno da citacao e peticionar rapidamente em caso de frustracao.",
            "peticao_manifestacao_sobre_citacao",
            "Registrar status da comunicacao no controle interno de prazos.",
        )

    if categoria == "intimacao":
        return (
            "Ler integralmente o ato intimado e abrir tarefa com prazo para cumprir determinacao.",
            "peticao_conforme_conteudo_do_ato",
            "Intimacao efetivada normalmente dispara prazo processual.",
        )

    if categoria == "certidao":
        if "guia" in f or "custas" in f or "boleto" in f or "honorario" in f:
            return (
                "Cumprir recolhimento indicado na certidao e juntar comprovante nos autos.",
                "peticao_juntada_comprovante",
                "Confirmar se o ato exige antecedencia minima antes de audiencia.",
            )
        return (
            "Validar o conteudo certificador e praticar o ato subsequente indicado.",
            "peticao_manifestacao_sobre_certidao",
            "Certidoes podem conter comandos com prazo implicito.",
        )

    if "despacho" in f or "decisao" in f:
        return (
            "Cumprir exatamente os comandos do juizo e protocolar peticao de atendimento.",
            "peticao_cumprimento_despacho",
            "Conferir prazo especifico fixado no proprio ato judicial.",
        )

    return (
        "Revisar o evento no processo original e definir proximo passo processual.",
        "peticao_conforme_necessidade",
        "Sem acao automatica segura; depende da leitura integral do ato.",
    )


def montar_evento(mov: int, bloco: str) -> Evento:
    cabecalho = extrair_cabecalho(bloco)
    categoria = classificar_evento(cabecalho, bloco)
    providencia, peca, alerta = sugerir_providencia(categoria, cabecalho, bloco)
    resumo = clean_spaces(bloco[:320])
    return Evento(
        mov=mov,
        cabecalho=cabecalho,
        resumo=resumo,
        categoria=categoria,
        providencia=providencia,
        peca_sugerida=peca,
        alerta=alerta,
    )


def build_output(path: Path, eventos: List[Evento]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = []
    lines.append("# PLANO DE PROVIDENCIAS POS-DECISAO")
    lines.append("")
    lines.append(f"- origem: {path.name}")
    lines.append(f"- gerado_em: {now}")
    lines.append(
        "- objetivo: indicar o que fazer apos cada decisao/ato relevante para manter estrategia e prazos sob controle."
    )
    lines.append("")

    if not eventos:
        lines.append("## Resultado")
        lines.append("- Nenhum evento com acao clara foi detectado automaticamente.")
        lines.append("- Revisar o arquivo original e complementar manualmente.")
        return "\n".join(lines)

    counts: Dict[str, int] = {}
    for ev in eventos:
        counts[ev.categoria] = counts.get(ev.categoria, 0) + 1

    lines.append("## Panorama")
    for k in sorted(counts):
        lines.append(f"- {k}: {counts[k]}")
    lines.append("")

    lines.append("## Providencias por movimentacao")
    for ev in eventos:
        lines.append(f"### Mov. {ev.mov} - {ev.cabecalho}")
        lines.append(f"- categoria: {ev.categoria}")
        lines.append(f"- resumo: {ev.resumo}")
        lines.append(f"- o_que_fazer_agora: {ev.providencia}")
        lines.append(f"- peca_sugerida: {ev.peca_sugerida}")
        lines.append(f"- alerta_de_prazo: {ev.alerta}")
        lines.append("")

    lines.append("## Pendencias para confirmacao humana")
    lines.append("- Confirmar teor integral do ato no processo original antes de protocolar.")
    lines.append("- Confirmar termo inicial e termo final dos prazos no painel oficial do tribunal.")
    lines.append("- Validar se houve evento superveniente que altere o plano de acao.")
    lines.append("")
    return "\n".join(lines)


def processar_arquivo(path: Path, out_dir: Path) -> Path:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    body = extract_body(raw)
    by_mov = parse_movimentacoes(body)
    if not by_mov:
        by_mov = parse_blocos_documento(body)

    eventos: List[Evento] = []
    for mov in sorted(by_mov.keys()):
        bloco = by_mov[mov]
        ev = montar_evento(mov, bloco)
        if evento_relevante(ev.categoria, ev.cabecalho, bloco):
            eventos.append(ev)

    # Regra principal: quando houver decisoes, priorizar somente decisoes do juizo.
    decisoes = [ev for ev in eventos if ev.categoria == "decisao_judicial"]
    if decisoes:
        eventos = decisoes

    # Evita saida excessiva em processos muito volumosos.
    if len(eventos) > 80:
        eventos = eventos[-80:]

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"providencias_{path.stem}.md"
    out_file.write_text(build_output(path, eventos), encoding="utf-8")
    return out_file


def main():
    parser = argparse.ArgumentParser(description="Gera plano de providencias apos decisoes em processo integral")
    parser.add_argument("--texto-dir", default="acervo_pecas/texto_extraido")
    parser.add_argument("--saida-dir", default="acervo_pecas/indices/providencias_processos")
    args = parser.parse_args()

    texto_dir = Path(args.texto_dir)
    saida_dir = Path(args.saida_dir)

    files = sorted(texto_dir.glob("processo_*.md"))
    if not files:
        print("OK: nenhum processo_*.md encontrado.")
        return

    outputs: List[Path] = []
    for f in files:
        outputs.append(processar_arquivo(f, saida_dir))

    print(f"OK: planos gerados={len(outputs)}")
    for o in outputs:
        print(o)


if __name__ == "__main__":
    main()
