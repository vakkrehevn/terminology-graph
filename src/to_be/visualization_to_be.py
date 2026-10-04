from pathlib import Path
from textwrap import wrap

import pandas as pd
from graphviz import Digraph, Source, unflatten


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "to_be"
    / "term_decisions_TO_BE_v0.2.xlsx"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "figures"
    / "to_be"
)

MAIN_SHEET = "TO_BE_v0.1"
EXTRA_EDGES_SHEET = "Доп_связи"


# ============================================================
# SETTINGS
# ============================================================

# Читаем сверху вниз
RANKDIR = "TB"

# Для основной структурной картинки
# дополнительные функциональные связи пока не рисуем.
SHOW_EXTRA_EDGES = False

EXCLUDED_ACTIONS = {
    "EXTERNAL",
    "REMOVE",
    "REVIEW",
}


# ============================================================
# PRIMARY EDGE STYLES
# ============================================================

PRIMARY_EDGE_STYLES = {
    "Group": {
        "color": "#999999",
        "style": "dashed",
        "penwidth": "1.1",
        "label": "",
    },

    "Is-A": {
        "color": "#1f4e79",
        "style": "solid",
        "penwidth": "1.7",
        "label": "",
    },

    "Part-Of": {
        "color": "#2e8b57",
        "style": "dashed",
        "penwidth": "1.6",
        "label": "",
    },

    "Role": {
        "color": "#7a3db8",
        "style": "dotted",
        "penwidth": "1.5",
        "label": "",
    },

    "Attribute": {
        "color": "#c97a00",
        "style": "dashdot",
        "penwidth": "1.4",
        "label": "",
    },

    "Related-To": {
        "color": "#777777",
        "style": "dashed",
        "penwidth": "1.2",
        "label": "",
    },
}


# ============================================================
# EXTRA EDGE STYLES
# ============================================================

EXTRA_EDGE_STYLES = {
    "Forms": {
        "color": "#7a3db8",
        "style": "dashed",
        "penwidth": "1.2",
        "label": "формирует",
    },

    "Organizes": {
        "color": "#555555",
        "style": "dotted",
        "penwidth": "1.2",
        "label": "организует",
    },

    "Regulates": {
        "color": "#c97a00",
        "style": "dashed",
        "penwidth": "1.2",
        "label": "регулирует",
    },

    "Provides": {
        "color": "#555555",
        "style": "dotted",
        "penwidth": "1.2",
        "label": "оказывает",
    },

    "Participates-In": {
        "color": "#555555",
        "style": "dotted",
        "penwidth": "1.2",
        "label": "участвует",
    },

    "Officiates-At": {
        "color": "#7a3db8",
        "style": "dotted",
        "penwidth": "1.2",
        "label": "судит",
    },

    "Conducts": {
        "color": "#555555",
        "style": "dotted",
        "penwidth": "1.2",
        "label": "проводит",
    },

    "Undergoes": {
        "color": "#555555",
        "style": "dotted",
        "penwidth": "1.2",
        "label": "проходит",
    },

    "Official-Status-Of": {
        "color": "#777777",
        "style": "dashed",
        "penwidth": "1.1",
        "label": "официальный статус",
    },
}


# ============================================================
# HELPERS
# ============================================================

def clean(value) -> str:
    """
    Excel value -> clean string.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize(value) -> str:
    return clean(value).upper()


def is_yes(value) -> bool:
    return normalize(value) in {
        "ДА",
        "YES",
        "TRUE",
        "1",
    }


def make_label(text: str) -> str:
    """
    Перенос длинных терминов,
    чтобы граф не растягивался по ширине.
    """

    lines = wrap(
        text,
        width=28,
        break_long_words=False,
        break_on_hyphens=False,
    )

    return "\\n".join(lines)


# ============================================================
# LOAD
# ============================================================

def load_data():
    """
    Читаем TO-BE из Excel.
    """

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            "\nНе найден TO-BE Excel:\n"
            f"{INPUT_FILE}\n\n"
            "Положи файл "
            "term_decisions_TO_BE_v0.2.xlsx "
            "в data/to_be/"
        )

    nodes_df = pd.read_excel(
        INPUT_FILE,
        sheet_name=MAIN_SHEET,
    )

    extra_edges_df = pd.read_excel(
        INPUT_FILE,
        sheet_name=EXTRA_EDGES_SHEET,
    )

    return nodes_df, extra_edges_df


# ============================================================
# SELECT NODES
# ============================================================

def select_nodes(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Оставляем только узлы,
    которые реально входят в TO-BE.
    """

    required = {
        "Тип узла",
        "Термин",
        "TO-BE действие",
        "TO-BE родитель",
        "TO-BE связь",
        "Семантический тип",
    }

    missing = required - set(df.columns)

    if missing:

        raise ValueError(
            "\nНа листе TO_BE_v0.1 "
            "не хватает колонок:\n"
            + "\n".join(
                sorted(missing)
            )
        )

    result = df.copy()

    result["TO-BE действие"] = (
        result["TO-BE действие"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    result = result[
        ~result[
            "TO-BE действие"
        ].isin(
            EXCLUDED_ACTIONS
        )
    ].copy()

    result = result.dropna(
        subset=["Термин"]
    )

    return result


# ============================================================
# ADD NODES
# ============================================================

def add_nodes(
    graph: Digraph,
    nodes_df: pd.DataFrame,
):
    """
    Добавляет узлы.

    Возвращает:
        term -> graphviz id
    """

    terms = (
        nodes_df["Термин"]
        .astype(str)
        .str.strip()
        .tolist()
    )

    term_to_id = {
        term: f"n{i}"
        for i, term in enumerate(
            terms
        )
    }

    for _, row in nodes_df.iterrows():

        term = clean(
            row["Термин"]
        )

        node_type = normalize(
            row["Тип узла"]
        )

        action = normalize(
            row["TO-BE действие"]
        )

        node_id = term_to_id[
            term
        ]

        label = make_label(
            term
        )

        # ====================================================
        # TECHNICAL ROOT
        # ====================================================

        if term == (
            "Физическая культура и спорт"
        ):

            graph.node(
                node_id,
                label=label,
                shape="box",
                style="rounded,filled",
                fillcolor="#eeeeee",
                color="#555555",
                penwidth="1.8",
                fontname="Arial",
                fontsize="14",
            )

        # ====================================================
        # MAIN DOMAIN NODES
        # ====================================================

        elif term in {
            "Спорт",
            "Физическая культура",
        }:

            graph.node(
                node_id,
                label=label,
                shape="plain",
                fontname="Arial Bold",
                fontsize="14",
            )

        # ====================================================
        # MODEL NODE
        # ====================================================

        elif node_type == "MODEL":

            graph.node(
                node_id,
                label=(
                    f"[MODEL]\\n"
                    f"{label}"
                ),
                shape="box",
                style="rounded,filled",
                fillcolor="#f2f2f2",
                color="#888888",
                fontcolor="#555555",
                fontname="Arial",
                fontsize="9",
            )

        # ====================================================
        # NEW TERM
        # ====================================================

        elif (
            node_type
            == "SUPERVISOR_ADD"
        ):

            graph.node(
                node_id,
                label=(
                    f"[NEW]\\n"
                    f"{label}"
                ),
                shape="box",
                style="rounded",
                color="#2e7d32",
                fontcolor="#2e7d32",
                penwidth="1.5",
                fontname="Arial Bold",
                fontsize="9",
            )

        # ====================================================
        # NORMAL TERM
        # ====================================================

        else:

            graph.node(
                node_id,
                label=label,
                shape="plain",
                fontname="Arial",
                fontsize="9",
            )

    return term_to_id


# ============================================================
# PRIMARY EDGES
# ============================================================

def add_primary_edges(
    graph: Digraph,
    nodes_df: pd.DataFrame,
    term_to_id: dict,
):
    """
    Главная структура TO-BE
    строится по колонкам:

        TO-BE родитель
        TO-BE связь
    """

    unresolved = []

    for _, row in nodes_df.iterrows():

        child = clean(
            row["Термин"]
        )

        parent = clean(
            row["TO-BE родитель"]
        )

        relation = clean(
            row["TO-BE связь"]
        )

        # ----------------------------------------------
        # ROOT
        # ----------------------------------------------

        if not parent:
            continue

        if (
            relation.lower()
            == "root"
        ):
            continue

        if (
            child
            not in term_to_id
        ):
            continue

        # ----------------------------------------------
        # PARENT MISSING
        # ----------------------------------------------

        if (
            parent
            not in term_to_id
        ):

            unresolved.append(
                {
                    "parent": parent,
                    "child": child,
                    "relation": relation,
                }
            )

            continue

        style = (
            PRIMARY_EDGE_STYLES
            .get(
                relation,
                {
                    "color": "#555555",
                    "style": "solid",
                    "penwidth": "1.3",
                    "label": "",
                },
            )
        )

        graph.edge(
            term_to_id[parent],
            term_to_id[child],

            color=style[
                "color"
            ],

            style=style[
                "style"
            ],

            penwidth=style[
                "penwidth"
            ],

            label=style[
                "label"
            ],

            arrowhead="normal",

            # Основные связи
            # формируют иерархию.
            constraint="true",

            weight="6",
        )

    return unresolved


# ============================================================
# EXTRA EDGES
# ============================================================

def add_extra_edges(
    graph: Digraph,
    extra_edges_df: pd.DataFrame,
    term_to_id: dict,
):
    """
    Вторичные функциональные отношения.

    Они не должны влиять
    на основную раскладку.
    """

    if (
        extra_edges_df.empty
    ):
        return

    required = {
        "Источник",
        "Цель",
        "Связь",
    }

    missing = (
        required
        - set(
            extra_edges_df.columns
        )
    )

    if missing:

        raise ValueError(
            "\nНа листе Доп_связи "
            "не хватает колонок:\n"
            + "\n".join(
                sorted(missing)
            )
        )

    for _, row in (
        extra_edges_df.iterrows()
    ):

        source = clean(
            row["Источник"]
        )

        target = clean(
            row["Цель"]
        )

        relation = clean(
            row["Связь"]
        )

        # ----------------------------------------------
        # INCLUDE?
        # ----------------------------------------------

        if (
            "Включать?"
            in extra_edges_df.columns
        ):

            include_value = clean(
                row.get(
                    "Включать?",
                    "",
                )
            )

            if (
                include_value
                and not is_yes(
                    include_value
                )
            ):
                continue

        # ----------------------------------------------
        # BOTH NODES MUST EXIST
        # ----------------------------------------------

        if (
            source
            not in term_to_id
            or target
            not in term_to_id
        ):
            continue

        style = (
            EXTRA_EDGE_STYLES
            .get(
                relation,
                {
                    "color": "#777777",
                    "style": "dotted",
                    "penwidth": "1.1",
                    "label": relation,
                },
            )
        )

        graph.edge(
            term_to_id[source],
            term_to_id[target],

            color=style[
                "color"
            ],

            style=style[
                "style"
            ],

            penwidth=style[
                "penwidth"
            ],

            label=style[
                "label"
            ],

            fontname="Arial",

            fontsize="7",

            arrowsize="0.65",

            # Не ломаем основную структуру.
            constraint="false",
        )


# ============================================================
# BUILD GRAPH
# ============================================================

def build_graph(
    all_rows_df: pd.DataFrame,
    extra_edges_df: pd.DataFrame,
):

    nodes_df = select_nodes(
        all_rows_df
    )

    graph = Digraph(
        "to_be_v02",
        engine="dot",
    )

    # ========================================================
    # GRAPH SETTINGS
    # ========================================================

    graph.attr(
        rankdir=RANKDIR,

        splines="spline",

        overlap="false",

        concentrate="false",

        newrank="true",

        # Узлы одного уровня
        # ближе друг к другу.
        nodesep="0.10",

        # Между уровнями
        # оставляем пространство.
        ranksep="0.65",

        pad="0.10",

        margin="0",

        ratio="compress",

        bgcolor="white",
    )

    graph.attr(
        "node",
        fontname="Arial",
        fontsize="9",
    )

    graph.attr(
        "edge",
        fontname="Arial",
        fontsize="7",
        arrowsize="0.65",
    )

    # ========================================================
    # NODES
    # ========================================================

    term_to_id = add_nodes(
        graph,
        nodes_df,
    )

    # ========================================================
    # PRIMARY EDGES
    # ========================================================

    unresolved = (
        add_primary_edges(
            graph,
            nodes_df,
            term_to_id,
        )
    )

    # ========================================================
    # EXTRA EDGES
    # ========================================================

    if SHOW_EXTRA_EDGES:

        add_extra_edges(
            graph,
            extra_edges_df,
            term_to_id,
        )

    return (
        graph,
        nodes_df,
        unresolved,
    )


# ============================================================
# RENDER
# ============================================================

def render_graph(
    graph: Digraph,
):
    """
    Делает более компактный граф.

    Graphviz unflatten:
    не позволяет большому числу листьев
    выстроиться в одну длинную строку.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    base_path = (
        OUTPUT_DIR
        / "to_be_v02_compact"
    )

    # ========================================================
    # RAW DOT
    # ========================================================

    dot_source = graph.source

    # ========================================================
    # UNFLATTEN
    # ========================================================

    compact_dot = unflatten(
        dot_source,

        # После нескольких листьев
        # Graphviz начинает переносить их.
        stagger=4,

        fanout=True,

        # Ограничиваем длинные
        # горизонтальные цепочки.
        chain=4,
    )

    compact_graph = Source(
        compact_dot,
        engine="dot",
    )

    # ========================================================
    # SVG
    # ========================================================

    compact_graph.render(
        filename=str(
            base_path
        ),
        format="svg",
        cleanup=True,
    )

    # ========================================================
    # PNG
    # ========================================================

    png_graph = Source(
        compact_dot,
        engine="dot",
        format="png",
    )

    png_graph.render(
        filename=str(
            base_path
        ),
        format="png",
        cleanup=True,
    )

    return base_path


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 70
    )

    print(
        "TO-BE v0.2 COMPACT GRAPH"
    )

    print(
        "=" * 70
    )

    # ========================================================
    # LOAD
    # ========================================================

    (
        all_rows_df,
        extra_edges_df,
    ) = load_data()

    # ========================================================
    # BUILD
    # ========================================================

    (
        graph,
        nodes_df,
        unresolved,
    ) = build_graph(
        all_rows_df,
        extra_edges_df,
    )

    # ========================================================
    # RENDER
    # ========================================================

    output_path = render_graph(
        graph
    )

    # ========================================================
    # STATS
    # ========================================================

    model_count = (
        nodes_df[
            "Тип узла"
        ]
        .fillna("")
        .astype(str)
        .str.upper()
        .eq("MODEL")
        .sum()
    )

    new_count = (
        nodes_df[
            "Тип узла"
        ]
        .fillna("")
        .astype(str)
        .str.upper()
        .eq(
            "SUPERVISOR_ADD"
        )
        .sum()
    )

    original_count = (
        nodes_df[
            "Тип узла"
        ]
        .fillna("")
        .astype(str)
        .str.upper()
        .eq("ORIGINAL")
        .sum()
    )

    print(
        f"\nУзлов в TO-BE: "
        f"{len(nodes_df)}"
    )

    print(
        f"  исходных терминов: "
        f"{original_count}"
    )

    print(
        f"  новых терминов: "
        f"{new_count}"
    )

    print(
        f"  MODEL-узлов: "
        f"{model_count}"
    )

    print(
        f"\nНеразрешённых "
        f"основных связей: "
        f"{len(unresolved)}"
    )

    if unresolved:

        print(
            "\nВНИМАНИЕ:"
        )

        for edge in unresolved:

            print(
                f"  "
                f"{edge['parent']}"
                f" -> "
                f"{edge['child']}"
                f" "
                f"({edge['relation']})"
            )

    if SHOW_EXTRA_EDGES:

        print(
            f"\nДополнительные связи: "
            f"ВКЛЮЧЕНЫ"
        )

    else:

        print(
            "\nДополнительные связи: "
            "СКРЫТЫ"
        )

    print(
        "\nСозданы:"
    )

    print(
        f"{output_path}.svg"
    )

    print(
        f"{output_path}.png"
    )


if __name__ == "__main__":
    main()