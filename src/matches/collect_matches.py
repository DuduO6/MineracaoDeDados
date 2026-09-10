"""Write the ten latest verified official derbies as an auditable snapshot."""
from __future__ import annotations

from config import settings
from src.common import configure_logging, update_summary, write_csv_atomic

FIELDS = ["match_id", "match_date", "match_datetime", "competition", "season", "home_team", "away_team", "home_score", "away_score", "winner", "atletico_score", "cruzeiro_score", "result_atletico", "result_cruzeiro", "source", "source_url"]

# Checked on 2026-09-09. Official club/CBF match reports are retained per row.
MATCHES = [
    ("2026-09-01-cam-cru", "2026-09-01", "2026-09-01T21:00:00-03:00", "Copa do Brasil - quartas de final (volta)", 2026, "Atlético-MG", "Cruzeiro", 2, 1, "CBF", "https://www.cbf.com.br/futebol-brasileiro/noticias/copa-brasil/a/atletico-mg-bate-cruzeiro-de-virada-e-o-primeiro-semifinalista-da-copa-do-brasil"),
    ("2026-08-25-cru-cam", "2026-08-25", "2026-08-25T21:00:00-03:00", "Copa do Brasil - quartas de final (ida)", 2026, "Cruzeiro", "Atlético-MG", 1, 1, "Clube Atlético Mineiro", "https://atletico.com.br/galo-empata-classico-e-leva-decisao-para-a-arena-mrv/"),
    ("2026-05-02-cru-cam", "2026-05-02", "2026-05-02T21:00:00-03:00", "Campeonato Brasileiro - 14ª rodada", 2026, "Cruzeiro", "Atlético-MG", 1, 3, "Clube Atlético Mineiro", "https://atletico.com.br/vitoria-gigante-no-classico-e-show-da-massa-no-mineirao/"),
    ("2026-03-08-cru-cam", "2026-03-08", "2026-03-08T18:00:00-03:00", "Campeonato Mineiro - final", 2026, "Cruzeiro", "Atlético-MG", 1, 0, "Clube Atlético Mineiro", "https://atletico.com.br/atletico-perde-a-final-do-mineiro-de-2026/"),
    ("2026-01-25-cam-cru", "2026-01-25", "2026-01-25T18:00:00-03:00", "Campeonato Mineiro - 5ª rodada", 2026, "Atlético-MG", "Cruzeiro", 2, 1, "Clube Atlético Mineiro", "https://atletico.com.br/galo-faz-valer-o-mando-e-vira-o-classico-na-arena-mrv/"),
    ("2025-10-15-cam-cru", "2025-10-15", "2025-10-15T21:30:00-03:00", "Campeonato Brasileiro - 28ª rodada", 2025, "Atlético-MG", "Cruzeiro", 1, 1, "Clube Atlético Mineiro", "https://atletico.com.br/galo-pressiona-mas-empata-classico-pelo-brasileirao/"),
    ("2025-09-11-cru-cam", "2025-09-11", "2025-09-11T19:30:00-03:00", "Copa do Brasil - quartas de final (volta)", 2025, "Cruzeiro", "Atlético-MG", 2, 0, "Clube Atlético Mineiro", "https://atletico.com.br/atletico-perde-para-o-cruzeiro-na-copa-do-brasil/"),
    ("2025-08-27-cam-cru", "2025-08-27", "2025-08-27T19:30:00-03:00", "Copa do Brasil - quartas de final (ida)", 2025, "Atlético-MG", "Cruzeiro", 0, 2, "Clube Atlético Mineiro", "https://atletico.com.br/atletico-perde-para-o-cruzeiro-na-copa-do-brasil/"),
    ("2025-05-18-cru-cam", "2025-05-18", "2025-05-18T20:30:00-03:00", "Campeonato Brasileiro - 9ª rodada", 2025, "Cruzeiro", "Atlético-MG", 0, 0, "Clube Atlético Mineiro", "https://atletico.com.br/atletico-empata-com-o-cruzeiro-pelo-brasileirao/"),
    ("2025-02-09-cru-cam", "2025-02-09", "2025-02-09T16:00:00-03:00", "Campeonato Mineiro - 7ª rodada", 2025, "Cruzeiro", "Atlético-MG", 0, 2, "Clube Atlético Mineiro", "https://atletico.com.br/galo-com-retrospecto-positivo-recente-no-classico/"),
]


def build_rows() -> list[dict[str, object]]:
    rows = []
    for mid, date, dt, comp, season, home, away, hs, aws, source, url in MATCHES:
        winner = "draw" if hs == aws else (home if hs > aws else away)
        atletico_score = hs if home == "Atlético-MG" else aws
        cruzeiro_score = hs if home == "Cruzeiro" else aws
        ar = "draw" if atletico_score == cruzeiro_score else ("win" if atletico_score > cruzeiro_score else "loss")
        rows.append(dict(match_id=mid, match_date=date, match_datetime=dt, competition=comp, season=season, home_team=home, away_team=away, home_score=hs, away_score=aws, winner=winner, atletico_score=atletico_score, cruzeiro_score=cruzeiro_score, result_atletico=ar, result_cruzeiro={"win":"loss", "loss":"win", "draw":"draw"}[ar], source=source, source_url=url))
    assert len(rows) == 10 and len({r["match_id"] for r in rows}) == 10
    return rows


def main() -> None:
    configure_logging()
    rows = build_rows()
    write_csv_atomic(settings.RAW_DIR / "matches.csv", FIELDS, rows)
    update_summary(collection_started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), matches=len(rows), errors=[])


if __name__ == "__main__":
    main()
