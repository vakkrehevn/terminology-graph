from pathlib import Path

from graphviz import Source, unflatten

from src.loader import load_terminology
from src.visualization import build_as_is_graph
from src.visualization_plain import build_plain_graph

from src.to_be.visualization_to_be import (
    load_data,
    build_graph,
)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "figures"
    / "png"
)


# ============================================================
# NORMAL PNG EXPORT
# ============================================================

def render_png(
    graph,
    filename: str,
) -> Path:
    """
    Сохраняет обычный Graphviz-граф
    в PNG высокого разрешения.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    graph.attr(
        dpi="300",
        bgcolor="white",
    )

    output_path = (
        OUTPUT_DIR
        / filename
    )

    rendered = graph.render(
        filename=str(output_path),
        format="png",
        cleanup=True,
    )

    return Path(rendered)


# ============================================================
# COMPACT TO-BE PNG
# ============================================================

def render_compact_png(
    graph,
    filename: str,
) -> Path:
    """
    Сохраняет TO-BE через unflatten.

    Это нужно, чтобы большое количество
    дочерних узлов не растягивалось
    одной длинной горизонтальной полосой.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    compact_dot = unflatten(
        graph.source,
        stagger=4,
        fanout=True,
        chain=4,
    )

    compact_graph = Source(
        compact_dot,
        engine="dot",
        format="png",
    )

    # 300 dpi
    compact_graph.graph_attr.update(
        {
            "dpi": "300",
            "bgcolor": "white",
        }
    )

    output_path = (
        OUTPUT_DIR
        / filename
    )

    rendered = compact_graph.render(
        filename=str(output_path),
        format="png",
        cleanup=True,
    )

    return Path(rendered)


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # AS-IS DATA
    # ========================================================

    df = load_terminology()

    # ========================================================
    # 1. ПОЛНЫЙ AS-IS С РАМКАМИ
    # ========================================================

    grouped_graph = (
        build_as_is_graph(df)
    )

    grouped_png = render_png(
        grouped_graph,
        "01_as_is_full_grouped",
    )

    # ========================================================
    # 2. ПОЛНЫЙ AS-IS PLAIN
    # ========================================================

    plain_graph = (
        build_plain_graph(df)
    )

    plain_png = render_png(
        plain_graph,
        "02_as_is_full_plain",
    )

    # ========================================================
    # 3. ТОЛЬКО СПОРТ
    # ========================================================

    sport_df = df[
        df["Мета-Класс (L1)"]
        == "Спорт"
    ].copy()

    sport_graph = (
        build_plain_graph(
            sport_df
        )
    )

    sport_png = render_png(
        sport_graph,
        "03_as_is_sport_plain",
    )

    # ========================================================
    # 4. ТОЛЬКО ФИЗИЧЕСКАЯ КУЛЬТУРА
    # ========================================================

    physical_culture_df = df[
        df["Мета-Класс (L1)"]
        == "Физическая культура"
    ].copy()

    physical_culture_graph = (
        build_plain_graph(
            physical_culture_df
        )
    )

    physical_culture_png = render_png(
        physical_culture_graph,
        "04_as_is_physical_culture_plain",
    )

    # ========================================================
    # 5. TO-BE v0.2
    # ========================================================

    (
        to_be_rows_df,
        extra_edges_df,
    ) = load_data()

    (
        to_be_graph,
        to_be_nodes_df,
        unresolved,
    ) = build_graph(
        to_be_rows_df,
        extra_edges_df,
    )

    to_be_png = render_compact_png(
        to_be_graph,
        "05_to_be_v02_compact",
    )

    # ========================================================
    # RESULT
    # ========================================================

    print("=" * 70)
    print("FINAL PNG GRAPHS GENERATED")
    print("=" * 70)

    print(
        f"\nВсего AS-IS терминов: "
        f"{len(df)}"
    )

    print(
        f"Спорт: "
        f"{len(sport_df)}"
    )

    print(
        f"Физическая культура: "
        f"{len(physical_culture_df)}"
    )

    print(
        f"TO-BE узлов: "
        f"{len(to_be_nodes_df)}"
    )

    print(
        f"Неразрешённых TO-BE связей: "
        f"{len(unresolved)}"
    )

    print("\nСозданы PNG:")

    print(
        f"\n1. AS-IS с рамками:\n"
        f"   {grouped_png}"
    )

    print(
        f"\n2. AS-IS plain:\n"
        f"   {plain_png}"
    )

    print(
        f"\n3. AS-IS — только Спорт:\n"
        f"   {sport_png}"
    )

    print(
        f"\n4. AS-IS — только "
        f"Физическая культура:\n"
        f"   {physical_culture_png}"
    )

    print(
        f"\n5. TO-BE v0.2:\n"
        f"   {to_be_png}"
    )


if __name__ == "__main__":
    main()