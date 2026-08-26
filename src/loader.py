from pathlib import Path

import pandas as pd


# Корень проекта:
# terminology-ontology-audit/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Исходная таблица
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "terminology.xlsx"


EXPECTED_COLUMNS = [
    "Термин",
    "Мета-Класс (L1)",
    "Функциональный класс (L2)",
    "Родительский узел",
    "Тип связи",
    "Критерий деления",
    "Дефект логики / Казус",
]


def load_terminology() -> pd.DataFrame:
    """
    Загружает исходную терминосистему из Excel,
    проверяет структуру и очищает пустые строки.
    """

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Файл с терминами не найден: {DATA_PATH}"
        )

    df = pd.read_excel(DATA_PATH)

    # Проверяем структуру Excel
    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"В таблице отсутствуют колонки: {missing_columns}"
        )

    # Оставляем только нужные колонки
    df = df[EXPECTED_COLUMNS].copy()

    # Удаляем полностью пустые строки
    df = df.dropna(how="all")

    # Строка без термина не может быть узлом графа
    df = df.dropna(subset=["Термин"])

    # Убираем случайные пробелы
    for column in EXPECTED_COLUMNS:
        if df[column].dtype == "object":
            df[column] = df[column].apply(
                lambda value: value.strip()
                if isinstance(value, str)
                else value
            )

    # Перестраиваем индекс
    df = df.reset_index(drop=True)

    return df


def print_dataset_info(df: pd.DataFrame) -> None:
    """Печатает базовую информацию об исходной терминосистеме."""

    print("=" * 60)
    print("TERMINOLOGY DATASET")
    print("=" * 60)

    print(f"\nКоличество терминов: {len(df)}")

    print("\nКолонки:")
    for column in df.columns:
        print(f"  - {column}")

    print("\nТипы связей:")
    print(df["Тип связи"].value_counts(dropna=False))

    print("\nМета-классы L1:")
    print(df["Мета-Класс (L1)"].value_counts(dropna=False))

    print("\nФункциональные классы L2:")
    print(df["Функциональный класс (L2)"].value_counts(dropna=False))

    print("\nПервые 5 терминов:")
    print(
        df[
            [
                "Термин",
                "Родительский узел",
                "Тип связи",
            ]
        ].head()
    )


if __name__ == "__main__":
    terminology = load_terminology()
    print_dataset_info(terminology)