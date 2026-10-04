from pathlib import Path
from textwrap import wrap

import pandas as pd
from graphviz import Digraph

from src.loader import load_terminology


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "figures"
)


# ============================================================
# RELATION STYLES
# ============================================================

RELATION_STYLES = {
    "Is-A": {
        "style": "solid",
        "penwidth": "1.8",
        "color": "#1f4e79",
    },

    "Part-Of": {
        "style": "dashed",
        "penwidth": "1.5",
        "color": "#2e8b57",
    },

    "Role": {
        "style": "dotted",
        "penwidth": "1.5",
        "color": "#7a3db8",
    },

    "Attribute": {
        "style": "dashdot",
        "penwidth": "1.3",
        "color": "#c97a00",
    },
}


# ============================================================
# HELPERS
# ============================================================

def clean(value):
    """
    Преобразует NaN в пустую строку.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def make_label(
    text: str,
    width: int = 25,
) -> str:
    """
    Переносит длинные названия на несколько строк.

    Это главное изменение для уменьшения
    ширины всего графа.
    """

    text = clean(text)

    if not text:
        return ""

    lines = wrap(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )

    return "\n".join(lines)


# ============================================================
# BUILD GRAPH
# ============================================================

def build_as_is_graph(
    df: pd.DataFrame,
) -> Digraph:
    """
    Строит визуальный AS-IS граф.

    ВАЖНО:
    - создаются только 69 терминов статьи;
    - L1 и L2 используются только
      для визуальной группировки;
    - никаких helper-узлов не создаётся;
    - длинные названия переносятся,
      чтобы граф не растягивался по ширине.
    """

    graph = Digraph(
        "terminology_as_is",
        format="svg",
        engine="dot",
    )

    # ========================================================
    # GRAPH SETTINGS
    # ========================================================

    graph.attr(
        # Сверху вниз
        rankdir="TB",

        # Более естественные линии.
        # ortho часто сильнее растягивает такой граф.
        splines="spline",

        overlap="false",

        concentrate="false",

        newrank="true",

        # ----------------------------------------------------
        # ГЛАВНОЕ ДЛЯ ШИРИНЫ
        # ----------------------------------------------------

        # Было 0.45.
        # Сильно сближаем соседние узлы.
        nodesep="0.15",

        # Расстояние между уровнями.
        ranksep="0.65",

        # Просим Graphviz компактнее упаковывать layout.
        ratio="compress",

        # Кластеры стараемся держать компактно.
        pack="true",

        packmode="cluster",

        bgcolor="white",

        pad="0.12",

        margin="0",
    )

    # ========================================================
    # NODE SETTINGS
    # ========================================================

    graph.attr(
        "node",

        shape="box",

        style="rounded",

        fontname="Arial",

        # Было 10.
        fontsize="9",

        # Чуть меньше внутренние поля.
        margin="0.08,0.05",
    )

    # ========================================================
    # EDGE SETTINGS
    # ========================================================

    graph.attr(
        "edge",

        fontname="Arial",

        fontsize="7",

        arrowsize="0.65",
    )

    # ========================================================
    # ALL REAL ARTICLE TERMS
    # ========================================================

    terms = set(
        df["Термин"].map(
            clean
        )
    )

    # Стабильный технический ID.
    term_to_id = {
        term: f"T{index:03d}"
        for index, term
        in enumerate(
            sorted(terms),
            start=1,
        )
    }

    # ========================================================
    # 1. VISUAL L1/L2 GROUPS
    # ========================================================

    for (
        l1_name,
        l1_df,
    ) in df.groupby(
        "Мета-Класс (L1)",
        dropna=False,
    ):

        l1_name = clean(
            l1_name
        )

        with graph.subgraph(
            name=(
                f"cluster_l1_"
                f"{abs(hash(l1_name))}"
            )
        ) as l1_cluster:

            l1_cluster.attr(
                # L1 тоже переносим,
                # если название длинное.
                label=make_label(
                    l1_name,
                    width=30,
                ),

                style="rounded",

                penwidth="2",

                fontsize="13",

                fontname="Arial Bold",

                # Уменьшаем внутреннее
                # пространство большого cluster.
                margin="10",
            )

            # =================================================
            # L2
            # =================================================

            for (
                l2_name,
                l2_df,
            ) in l1_df.groupby(
                "Функциональный класс (L2)",
                dropna=False,
            ):

                l2_name = clean(
                    l2_name
                )

                with l1_cluster.subgraph(
                    name=(
                        f"cluster_l2_"
                        f"{abs(hash((l1_name, l2_name)))}"
                    )
                ) as l2_cluster:

                    l2_cluster.attr(
                        label=make_label(
                            l2_name,
                            width=24,
                        ),

                        style="rounded,dashed",

                        fontsize="9",

                        fontname="Arial",

                        margin="7",
                    )

                    # =========================================
                    # TERMS
                    # =========================================

                    for _, row in (
                        l2_df.iterrows()
                    ):

                        term = clean(
                            row["Термин"]
                        )

                        # Ключевой момент:
                        # длинный термин занимает
                        # несколько строк вместо
                        # огромной горизонтальной коробки.
                        display_label = make_label(
                            term,
                            width=24,
                        )

                        # Главные термины
                        if term in {
                            "Спорт",
                            "Физическая культура",
                        }:

                            l2_cluster.node(
                                term_to_id[term],

                                label=display_label,

                                fontsize="12",

                                penwidth="1.8",

                                fontname="Arial Bold",

                                tooltip=(
                                    f"L1: "
                                    f"{clean(row['Мета-Класс (L1)'])}\n"

                                    f"L2: "
                                    f"{clean(row['Функциональный класс (L2)'])}\n"

                                    f"Критерий: "
                                    f"{clean(row['Критерий деления'])}"
                                ),
                            )

                        else:

                            l2_cluster.node(
                                term_to_id[term],

                                label=display_label,

                                tooltip=(
                                    f"L1: "
                                    f"{clean(row['Мета-Класс (L1)'])}\n"

                                    f"L2: "
                                    f"{clean(row['Функциональный класс (L2)'])}\n"

                                    f"Критерий: "
                                    f"{clean(row['Критерий деления'])}"
                                ),
                            )

    # ========================================================
    # 2. REAL RELATIONS FROM TABLE
    # ========================================================

    for _, row in df.iterrows():

        child = clean(
            row["Термин"]
        )

        parent = clean(
            row["Родительский узел"]
        )

        relation = clean(
            row["Тип связи"]
        )

        if (
            not parent
            or parent in {
                "—",
                "-",
            }
        ):
            continue

        # Если родителя нет среди терминов статьи,
        # нового узла НЕ создаём.
        if parent not in terms:
            continue

        if relation == "Root":
            continue

        style = RELATION_STYLES.get(
            relation,
            {
                "style": "solid",
                "penwidth": "1.0",
                "color": "#555555",
            },
        )

        is_structural = (
            relation
            in {
                "Is-A",
                "Part-Of",
            }
        )

        graph.edge(
            term_to_id[parent],

            term_to_id[child],

            label="",

            style=style[
                "style"
            ],

            penwidth=style[
                "penwidth"
            ],

            color=style[
                "color"
            ],

            fontcolor=style[
                "color"
            ],

            arrowhead="normal",

            constraint=(
                "true"
                if is_structural
                else "false"
            ),

            weight=(
                "6"
                if is_structural
                else "1"
            ),
        )

    return graph


# ============================================================
# MAIN
# ============================================================

def main():

    df = load_terminology()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    graph = build_as_is_graph(
        df
    )

    output_path = (
        OUTPUT_DIR
        / "as_is_terminology_graph_compact"
    )

    rendered = graph.render(
        filename=str(
            output_path
        ),
        cleanup=True,
    )

    print(
        "=" * 60
    )

    print(
        "AS-IS COMPACT GRAPH GENERATED"
    )

    print(
        "=" * 60
    )

    print(
        f"\nТерминов: "
        f"{len(df)}"
    )

    print(
        f"Файл: "
        f"{rendered}"
    )


if __name__ == "__main__":
    main()