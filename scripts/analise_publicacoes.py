"""Resumo das publicações e coletas de um período, para ajustar o volume.

Uso:
    python -m scripts.analise_publicacoes            # últimas 3 horas
    python -m scripts.analise_publicacoes --horas 8
"""

import argparse

from sqlalchemy import text

from ofertas.core.config import get_settings
from ofertas.db.session import engine

FUSO = "America/Sao_Paulo"


def _secao(titulo: str) -> None:
    print(f"\n== {titulo}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--horas", type=float, default=3)
    args = parser.parse_args()
    p = {"h": f"{args.horas} hours", "fuso": FUSO}

    with engine.connect() as c:
        config = c.execute(
            text("SELECT limite_publicacoes_por_ciclo, limite_produtos_por_categoria, validade_preco_minutos FROM configuracoes_sistema")
        ).one()
        intervalo = c.execute(text("SELECT intervalo_publicacao_minutos FROM configuracoes_divulgacao LIMIT 1")).scalar()
        agora = c.execute(text("SELECT to_char(now() AT TIME ZONE :fuso, 'DD/MM HH24:MI')"), p).scalar()
        print(f"Análise das últimas {args.horas:g}h (até {agora})")
        print(
            f"Config: teto {config[0]}/ciclo, {config[1]}/categoria, ciclo a cada {intervalo} min, "
            f"validade do preço {config[2]} min, desconto máximo {get_settings().desconto_maximo_percentual}%"
        )

        base = """FROM publicacoes pu JOIN produtos pr ON pr.id = pu.produto_id
                  JOIN plataformas pl ON pl.id = pr.plataforma_id
                  LEFT JOIN plataforma_categoria pc ON pc.id = pr.categoria_id
                  WHERE pu.created_at > now() - CAST(:h AS interval)"""

        _secao("Publicações")
        total = dict(c.execute(text(f"SELECT pu.status_publicacao, count(*) {base} GROUP BY 1"), p).all())
        print(f"  status: {total or 'nenhuma'}")
        publicadas = total.get("publicada", 0)
        if publicadas:
            print(f"  média: {publicadas / args.horas:.1f} por hora (projeção 07h–23h: ~{publicadas / args.horas * 16:.0f}/dia)")
            for hora, n in c.execute(
                text(f"SELECT to_char(pu.publicada_em AT TIME ZONE :fuso, 'HH24\"h\"'), count(*) {base} AND pu.status_publicacao = 'publicada' GROUP BY 1 ORDER BY 1"),
                p,
            ):
                print(f"    {hora}: {n}")
            espaco = c.execute(
                text(f"""SELECT avg(d), min(d) FROM (SELECT extract(epoch FROM pu.publicada_em - lag(pu.publicada_em)
                         OVER (ORDER BY pu.publicada_em)) d {base} AND pu.status_publicacao = 'publicada') x WHERE d < 600"""),
                p,
            ).one()
            if espaco[0]:
                print(f"  espaço entre mensagens: média {espaco[0]:.0f}s, mínimo {espaco[1]:.0f}s")

        if publicadas:
            _secao("Qualidade do que saiu")
            q = c.execute(
                text(f"""SELECT avg(pr.percentual_desconto), percentile_cont(0.5) WITHIN GROUP (ORDER BY pr.percentual_desconto),
                         count(*) FILTER (WHERE pr.posicao_selecao_categoria <= 10), count(*) FILTER (WHERE pr.posicao_selecao_categoria IS NULL),
                         max(extract(epoch FROM pu.publicada_em - pr.ultima_coleta_em) / 60)
                         {base} AND pu.status_publicacao = 'publicada'"""),
                p,
            ).one()
            print(f"  desconto: média {q[0]:.1f}%, mediana {q[1]:.1f}%")
            print(f"  entre os 10 mais populares da categoria: {q[2]} de {publicadas} ({q[2] * 100 / publicadas:.0f}%); sem posição: {q[3]}")
            print(f"  preço mais antigo no envio: {q[4]:.0f} min")

            _secao("Variedade")
            for loja, n in c.execute(text(f"SELECT pl.nome, count(*) {base} AND pu.status_publicacao = 'publicada' GROUP BY 1 ORDER BY 2 DESC"), p):
                print(f"  {loja}: {n} ({n * 100 / publicadas:.0f}%)")
            categorias = c.execute(
                text(f"SELECT pc.nome_categoria, count(*) {base} AND pu.status_publicacao = 'publicada' GROUP BY 1 ORDER BY 2 DESC"), p
            ).all()
            print(f"  {len(categorias)} categorias diferentes; as que mais saíram: "
                  + ", ".join(f"{nome} ({n})" for nome, n in categorias[:5]))

        _secao("Ciclos")
        for linha in c.execute(
            text("""SELECT to_char(iniciado_em AT TIME ZONE :fuso, 'HH24:MI'), status, quantidade_candidatos,
                    quantidade_publicada, quantidade_ignorada, quantidade_falha,
                    round(extract(epoch FROM coalesce(finalizado_em, now()) - iniciado_em) / 60)
                    FROM ciclos_publicacao WHERE iniciado_em > now() - CAST(:h AS interval) ORDER BY id"""),
            p,
        ):
            print(f"  {linha[0]} {linha[1]:<12} candidatos {linha[2]:>3} | publicadas {linha[3]:>3} ignoradas {linha[4]} falhas {linha[5]} | {linha[6]:.0f} min")

        _secao("Estoque para os próximos ciclos")
        estoque = c.execute(
            text("""SELECT count(*), count(DISTINCT categoria_id) FROM produtos pr
                    WHERE elegivel_divulgacao AND ultima_coleta_em > now() - make_interval(mins => :v)
                    AND NOT EXISTS (SELECT 1 FROM publicacoes pu WHERE pu.produto_id = pr.id
                                    AND pu.status_publicacao = 'publicada' AND pu.publicada_em > now() - interval '24 hours')"""),
            {"v": config[2]},
        ).one()
        print(f"  {estoque[0]} produtos elegíveis, com preço válido e não publicados nas últimas 24h, em {estoque[1]} categorias")
        print("  (se ficar perto do teto por ciclo, falta estoque de boas ofertas para subir o volume)")

        _secao("Coletas")
        for linha in c.execute(
            text("""SELECT pl.nome, e.status, e.quantidade_processada, e.quantidade_ignorada,
                    to_char(e.iniciada_em AT TIME ZONE :fuso, 'HH24:MI'),
                    round(extract(epoch FROM coalesce(e.finalizada_em, now()) - e.iniciada_em) / 60)
                    FROM execucoes_coleta e JOIN plataformas pl ON pl.id = e.plataforma_id
                    WHERE e.iniciada_em > now() - CAST(:h AS interval) ORDER BY e.id"""),
            p,
        ):
            print(f"  {linha[4]} {linha[0]:<14} {linha[1]:<12} processados {linha[2]:>5} ignorados {linha[3]:>5} | {linha[5]:.0f} min")


if __name__ == "__main__":
    main()
