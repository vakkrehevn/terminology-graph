from pathlib import Path

import pandas as pd

from src.loader import load_terminology


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

NODES_PATH = PROCESSED_DIR / "nodes.csv"
EDGES_PATH = PROCESSED_DIR / "edges.csv"


NO_PARENT_VALUES = {"—", "-", "", None}


def build_nodes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Формирует таблицу узлов графа.

    statutory — термин непосредственно из исходной статьи;
    helper    — вспомогательный классификационный узел,
                введённый при построении структуры.
    """

    statutory_terms = set(df["Термин"])

    parents = {
        parent
        for parent in df["Родительский узел"].dropna()
        if parent not in NO_PARENT_VALUES
    }

    helper_terms = sorted(parents - statutory_terms)

    nodes = []

    # Термины исходной статьи
    for index, row in df.iterrows():
        nodes.append(
            {
                "node_id": f"T{index + 1:03d}",
                "label": row["Термин"],
                "origin": "statutory",
                "meta_class_l1": row["Мета-Класс (L1)"],
                "functional_class_l2": row["Функциональный класс (L2)"],
                "criterion": row["Критерий деления"],
                "defect_note": row["Дефект логики / Казус"],
            }
        )

    # Вспомогательные узлы
    for index, helper in enumerate(helper_terms, start=1):
        nodes.append(
            {
                "node_id": f"H{index:03d}",
                "label": helper,
                "origin": "helper",
                "meta_class_l1": None,
                "functional_class_l2": "Helper",
                "criterion": None,
                "defect_note": None,
            }
        )

    return pd.DataFrame(nodes)


def build_edges(
    df: pd.DataFrame,
    nodes: pd.DataFrame,
) -> pd.DataFrame:
    """
    Формирует рёбра графа.

    Направление:
        термин -> родитель

    Например:
        Массовый спорт -> Спорт
        relation = Is-A
    """

    label_to_id = dict(
        zip(nodes["label"], nodes["node_id"])
    )

    edges = []

    for _, row in df.iterrows():
        child = row["Термин"]
        parent = row["Родительский узел"]

        if pd.isna(parent) or parent in NO_PARENT_VALUES:
            continue

        edges.append(
            {
                "source_id": label_to_id[child],
                "source_label": child,
                "target_id": label_to_id[parent],
                "target_label": parent,
                "relation": row["Тип связи"],
            }
        )

    return pd.DataFrame(edges)


def validate_dataset(
    df: pd.DataFrame,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
) -> None:
    """
    Выполняет несколько базовых проверок перед построением графа.
    """

    print("\n" + "=" * 60)
    print("DATASET VALIDATION")
    print("=" * 60)

    statutory_count = (
        nodes["origin"] == "statutory"
    ).sum()

    helper_count = (
        nodes["origin"] == "helper"
    ).sum()

    print(f"\nТермины статьи: {statutory_count}")
    print(f"Вспомогательные узлы: {helper_count}")
    print(f"Всего узлов: {len(nodes)}")
    print(f"Всего рёбер: {len(edges)}")

    helper_nodes = nodes[
        nodes["origin"] == "helper"
    ]["label"].tolist()

    print("\nВспомогательные узлы:")

    for node in helper_nodes:
        print(f"  [HELPER] {node}")

    # Root, у которого при этом указан родитель
    suspicious_roots = df[
        (df["Тип связи"] == "Root")
        & (~df["Родительский узел"].isin(NO_PARENT_VALUES))
        & (df["Родительский узел"].notna())
    ]

    if not suspicious_roots.empty:
        print("\nПредупреждение: Root-узлы с указанным родителем:")

        for _, row in suspicious_roots.iterrows():
            print(
                f"  [ROOT_WITH_PARENT] "
                f"{row['Термин']} -> "
                f"{row['Родительский узел']}"
            )

    # Проверяем дубликаты терминов
    duplicates = df[
        df["Термин"].duplicated(keep=False)
    ]

    if duplicates.empty:
        print("\nДубликаты терминов: не обнаружены")
    else:
        print("\nОбнаружены дубликаты терминов:")

        for term in duplicates["Термин"].unique():
            print(f"  [DUPLICATE] {term}")


def save_dataset(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
) -> None:

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    nodes.to_csv(
        NODES_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    edges.to_csv(
        EDGES_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nФайлы сохранены:")
    print(f"  {NODES_PATH}")
    print(f"  {EDGES_PATH}")


def main() -> None:
    df = load_terminology()

    nodes = build_nodes(df)
    edges = build_edges(df, nodes)

    validate_dataset(
        df,
        nodes,
        edges,
    )

    save_dataset(
        nodes,
        edges,
    )


if __name__ == "__main__":
    main()