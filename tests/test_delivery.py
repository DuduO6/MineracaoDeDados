import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_ids(path: Path, column: str) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [row[column] for row in csv.DictReader(handle)]


def test_snapshot_relations_are_complete_and_unique():
    match_ids = read_ids(ROOT / "data/raw/matches.csv", "match_id")
    video_ids = read_ids(ROOT / "data/raw/videos.csv", "video_id")

    with (ROOT / "data/raw/videos.csv").open(encoding="utf-8", newline="") as handle:
        video_rows = list(csv.DictReader(handle))
    with (ROOT / "data/raw/comments.csv").open(encoding="utf-8", newline="") as handle:
        comment_rows = list(csv.DictReader(handle))

    comment_ids = [row["comment_id"] for row in comment_rows]
    assert len(match_ids) == len(set(match_ids)) == 10
    assert len(video_ids) == len(set(video_ids)) == 100
    assert len(comment_ids) == len(set(comment_ids)) == 58_910
    assert {row["match_id"] for row in video_rows} <= set(match_ids)
    assert {row["video_id"] for row in comment_rows} <= set(video_ids)
    assert {row["match_id"] for row in comment_rows} <= set(match_ids)


def test_notebook_is_an_executed_error_free_delivery():
    notebook = json.loads((ROOT / "analysis.ipynb").read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    errors = [
        output
        for cell in code_cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    assert code_cells
    assert all(cell.get("execution_count") is not None for cell in code_cells)
    assert not errors


def test_sentiment_model_revision_is_reproducible():
    metadata = json.loads(
        (ROOT / "outputs/tables/nlp_metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["resolved_revision"]
    assert metadata["resolved_revision"] != "main"

    notebook = json.loads((ROOT / "analysis.ipynb").read_text(encoding="utf-8"))
    source = "".join(
        line
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
        for line in cell["source"]
    )
    assert f'SENTIMENT_REVISION = "{metadata["resolved_revision"]}"' in source
