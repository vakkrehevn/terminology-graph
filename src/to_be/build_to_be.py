from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "to_be"
    / "term_decisions.xlsx"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "to_be"
)

NODES_FILE = OUTPUT_DIR / "nodes_to_be.csv"
EDGES_FILE = OUTPUT_DIR / "edges_to_be.csv"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved_to_be.csv"


# ============================================================
# EXCEL SHEETS
# ============================================================

MAIN_SHEET = "Решения_по_терминам"
NEW_TERMS_SHEET = "Новые_термины"


# ============================================================
# STATUSES
# ============================================================

# Эти статусы НЕ попадают в TO-BE вообще.
EXCLUDED_STATUSES = {
    "REVIEW",
    "REMOVE",
    "EXTERNAL",
}


# ============================================================
# ROOT VALUES
# ============================================================

ROOT_VALUES = {
    "",
    "-",
    "—",
    "root",
    "none",
    "nan",
}


# ============================================================
# HELPERS
# ============================================================

def clean(value) -> str:
    """
    Приводит значение Excel к чистой строке.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_status(value) -> str:
    """
    Нормализует статус.
    """

    return clean(value).upper()


def is_empty_parent(value) -> bool:
    """
    Проверяет, является ли значение отсутствующим родителем.
    """

    value = clean(value)

    return value.lower() in ROOT_VALUES


# ============================================================
# LOAD MAIN DECISIONS
# ============================================================

def load_decisions() -> pd.DataFrame:
    """
    Загружает основной лист term_decisions.xlsx.
    """

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"\nНе найден файл:\n{INPUT_FILE}\n"
        )

    df = pd.read_excel(
        INPUT_FILE,
        sheet_name=MAIN_SHEET,
    )

    required_columns = {
        "Исходный термин",
        "Мета-класс L1",
        "Функциональный класс L2",
        "AS-IS родитель",
        "AS-IS связь",
        "Предварительный статус",
        "TO-BE родитель",
        "TO-BE связь",
        "Семантический тип",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            "\nВ term_decisions.xlsx отсутствуют колонки:\n"
            + "\n".join(sorted(missing))
        )

    df = df.dropna(
        subset=["Исходный термин"]
    ).copy()

    return df


# ============================================================
# LOAD NEW TERMS
# ============================================================

def load_new_terms() -> pd.DataFrame:
    """
    Загружает новые термины из проекта руководителя.
    """

    try:
        df = pd.read_excel(
            INPUT_FILE,
            sheet_name=NEW_TERMS_SHEET,
        )

    except ValueError:
        return pd.DataFrame()

    if "Новый термин" not in df.columns:
        return pd.DataFrame()

    df = df.dropna(
        subset=["Новый термин"]
    ).copy()

    return df


# ============================================================
# BUILD NODES
# ============================================================

def build_nodes(
    decisions_df: pd.DataFrame,
    new_terms_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Создаёт набор узлов TO-BE.

    В TO-BE включаются только термины со статусами:
    KEEP
    REDEFINE
    RENAME
    MOVE
    ADD

    REVIEW / REMOVE / EXTERNAL исключаются.
    """

    nodes = []

    # --------------------------------------------------------
    # 1. Исходные термины
    # --------------------------------------------------------

    for _, row in decisions_df.iterrows():

        term = clean(
            row["Исходный термин"]
        )

        status = normalize_status(
            row["Предварительный статус"]
        )

        # Не включаем в новую терминосистему.
        if status in EXCLUDED_STATUSES:
            continue

        nodes.append(
            {
                "term": term,

                # Откуда взялся термин
                "source": "article",

                # Старый или новый
                "is_new": False,

                # Решение
                "status": status,

                # Старые категории оставляем как метаданные.
                # Они НЕ определяют TO-BE структуру.
                "l1": clean(
                    row.get(
                        "Мета-класс L1",
                        "",
                    )
                ),

                "l2": clean(
                    row.get(
                        "Функциональный класс L2",
                        "",
                    )
                ),

                # TO-BE тип
                "semantic_type": clean(
                    row.get(
                        "Семантический тип",
                        "",
                    )
                ),

                "decision_comment": clean(
                    row.get(
                        "Решение / комментарий",
                        "",
                    )
                ),
            }
        )

    # --------------------------------------------------------
    # 2. Новые термины
    # --------------------------------------------------------

    if not new_terms_df.empty:

        for _, row in new_terms_df.iterrows():

            term = clean(
                row["Новый термин"]
            )

            status = normalize_status(
                row.get(
                    "Статус",
                    "ADD",
                )
            )

            if status in EXCLUDED_STATUSES:
                continue

            nodes.append(
                {
                    "term": term,
                    "source": "new_term",
                    "is_new": True,
                    "status": status,
                    "l1": "",
                    "l2": "",

                    "semantic_type": clean(
                        row.get(
                            "Семантический тип",
                            "",
                        )
                    ),

                    "decision_comment": clean(
                        row.get(
                            "Комментарий",
                            "",
                        )
                    ),
                }
            )

    nodes_df = pd.DataFrame(
        nodes,
        columns=[
            "term",
            "source",
            "is_new",
            "status",
            "l1",
            "l2",
            "semantic_type",
            "decision_comment",
        ],
    )

    if not nodes_df.empty:

        nodes_df = (
            nodes_df
            .drop_duplicates(
                subset=["term"],
                keep="first",
            )
            .reset_index(drop=True)
        )

    return nodes_df


# ============================================================
# BUILD EDGES
# ============================================================

def build_edges(
    decisions_df: pd.DataFrame,
    new_terms_df: pd.DataFrame,
    nodes_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Создаёт связи TO-BE.

    ВАЖНО:
    AS-IS связи больше автоматически НЕ переносятся.

    Связь создаётся только тогда, когда в Excel явно заполнены:
        TO-BE родитель
        TO-BE связь
    """

    edges = []
    unresolved = []

    terms = set(
        nodes_df["term"]
    )

    # --------------------------------------------------------
    # 1. Исходные термины
    # --------------------------------------------------------

    for _, row in decisions_df.iterrows():

        child = clean(
            row["Исходный термин"]
        )

        status = normalize_status(
            row["Предварительный статус"]
        )

        # Термин вообще не входит в TO-BE.
        if status in EXCLUDED_STATUSES:
            continue

        # ====================================================
        # БЕРЁМ ТОЛЬКО TO-BE
        # ====================================================

        parent = clean(
            row.get(
                "TO-BE родитель",
                "",
            )
        )

        relation = clean(
            row.get(
                "TO-BE связь",
                "",
            )
        )

        # ----------------------------------------------------
        # Пока родитель не определён
        # ----------------------------------------------------

        if is_empty_parent(parent):
            continue

        # ----------------------------------------------------
        # Пока тип связи не определён
        # ----------------------------------------------------

        if not relation:
            continue

        # ----------------------------------------------------
        # Root не создаёт ребро
        # ----------------------------------------------------

        if relation.lower() == "root":
            continue

        edge = {
            "parent": parent,
            "child": child,
            "relation": relation,
            "source": "TO-BE",
            "status": status,
        }

        # ----------------------------------------------------
        # Родитель существует в TO-BE
        # ----------------------------------------------------

        if parent in terms:

            edges.append(
                edge
            )

        # ----------------------------------------------------
        # Родителя пока нет в TO-BE
        # ----------------------------------------------------

        else:

            unresolved.append(
                {
                    **edge,

                    "reason": (
                        "TO-BE родитель отсутствует "
                        "среди узлов TO-BE"
                    ),
                }
            )

    # --------------------------------------------------------
    # 2. Новые термины
    # --------------------------------------------------------

    if not new_terms_df.empty:

        for _, row in new_terms_df.iterrows():

            child = clean(
                row["Новый термин"]
            )

            status = normalize_status(
                row.get(
                    "Статус",
                    "ADD",
                )
            )

            if status in EXCLUDED_STATUSES:
                continue

            parent = clean(
                row.get(
                    "TO-BE родитель",
                    "",
                )
            )

            relation = clean(
                row.get(
                    "TO-BE связь",
                    "",
                )
            )

            # Новый термин пока может просто существовать
            # без включения в иерархию.
            if is_empty_parent(parent):
                continue

            if not relation:

                unresolved.append(
                    {
                        "parent": parent,
                        "child": child,
                        "relation": "",
                        "source": "TO-BE",
                        "status": status,

                        "reason": (
                            "У нового термина "
                            "не заполнена TO-BE связь"
                        ),
                    }
                )

                continue

            if relation.lower() == "root":
                continue

            edge = {
                "parent": parent,
                "child": child,
                "relation": relation,
                "source": "TO-BE",
                "status": status,
            }

            if parent in terms:

                edges.append(
                    edge
                )

            else:

                unresolved.append(
                    {
                        **edge,

                        "reason": (
                            "TO-BE родитель нового термина "
                            "отсутствует среди узлов TO-BE"
                        ),
                    }
                )

    # ========================================================
    # DATAFRAMES
    # ========================================================

    edges_df = pd.DataFrame(
        edges,
        columns=[
            "parent",
            "child",
            "relation",
            "source",
            "status",
        ],
    )

    unresolved_df = pd.DataFrame(
        unresolved,
        columns=[
            "parent",
            "child",
            "relation",
            "source",
            "status",
            "reason",
        ],
    )

    if not edges_df.empty:

        edges_df = (
            edges_df
            .drop_duplicates()
            .reset_index(drop=True)
        )

    if not unresolved_df.empty:

        unresolved_df = (
            unresolved_df
            .drop_duplicates()
            .reset_index(drop=True)
        )

    return (
        edges_df,
        unresolved_df,
    )


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    unresolved_df: pd.DataFrame,
) -> None:
    """
    Сохраняет данные TO-BE.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    nodes_df.to_csv(
        NODES_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    edges_df.to_csv(
        EDGES_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    unresolved_df.to_csv(
        UNRESOLVED_FILE,
        index=False,
        encoding="utf-8-sig",
    )


# ============================================================
# REPORT
# ============================================================

def print_report(
    decisions_df: pd.DataFrame,
    new_terms_df: pd.DataFrame,
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    unresolved_df: pd.DataFrame,
) -> None:
    """
    Печатает статистику сборки.
    """

    print("\n" + "=" * 70)
    print("TO-BE DATASET BUILT")
    print("=" * 70)

    print(
        f"\nИсходных терминов в таблице: "
        f"{len(decisions_df)}"
    )

    print(
        f"Новых терминов: "
        f"{len(new_terms_df)}"
    )

    print(
        f"\nУзлов в TO-BE: "
        f"{len(nodes_df)}"
    )

    print(
        f"Связей в TO-BE: "
        f"{len(edges_df)}"
    )

    print(
        f"Неразрешённых TO-BE связей: "
        f"{len(unresolved_df)}"
    )

    # --------------------------------------------------------
    # Status counts
    # --------------------------------------------------------

    if not nodes_df.empty:

        print("\nСтатусы узлов:")

        print(
            nodes_df[
                "status"
            ].value_counts()
        )

    # --------------------------------------------------------
    # Relations
    # --------------------------------------------------------

    if not edges_df.empty:

        print("\nТипы TO-BE связей:")

        print(
            edges_df[
                "relation"
            ].value_counts()
        )

    # --------------------------------------------------------
    # Excluded original terms
    # --------------------------------------------------------

    excluded = decisions_df[
        decisions_df[
            "Предварительный статус"
        ]
        .astype(str)
        .str.upper()
        .isin(EXCLUDED_STATUSES)
    ]

    print(
        f"\nИсключено из текущего TO-BE: "
        f"{len(excluded)}"
    )

    if not excluded.empty:

        print("\nИсключённые / пока не включённые статусы:")

        print(
            excluded[
                "Предварительный статус"
            ]
            .astype(str)
            .str.upper()
            .value_counts()
        )

    # --------------------------------------------------------
    # Files
    # --------------------------------------------------------

    print("\nФайлы:")

    print(
        f"\nnodes:\n{NODES_FILE}"
    )

    print(
        f"\nedges:\n{EDGES_FILE}"
    )

    print(
        f"\nunresolved:\n{UNRESOLVED_FILE}"
    )

    if not unresolved_df.empty:

        print(
            "\nВНИМАНИЕ:"
            "\nЕсть TO-BE связи, для которых "
            "ещё не создан родительский узел."
        )

        print(
            "\nЭто не AS-IS fallback."
            "\nЭто именно незавершённые решения TO-BE."
        )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 70)
    print("BUILD TO-BE DATASET")
    print("=" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    decisions_df = load_decisions()

    new_terms_df = load_new_terms()

    # --------------------------------------------------------
    # Nodes
    # --------------------------------------------------------

    nodes_df = build_nodes(
        decisions_df,
        new_terms_df,
    )

    # --------------------------------------------------------
    # Edges
    # --------------------------------------------------------

    edges_df, unresolved_df = build_edges(
        decisions_df,
        new_terms_df,
        nodes_df,
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_results(
        nodes_df,
        edges_df,
        unresolved_df,
    )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    print_report(
        decisions_df,
        new_terms_df,
        nodes_df,
        edges_df,
        unresolved_df,
    )


if __name__ == "__main__":
    main()