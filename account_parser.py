#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

# -------------------------
# Настройка: укажи свои файлы
# -------------------------
GROUPS: Dict[str, List[str]] = {
    "CH": [
        r"chemodan_goods (3).txt",
        r"chem2_goods.txt",
        r"chemodan_goods (7).txt",
        r"chemodik_goods (2).txt",
        r"che_goods (2).txt",
        r"chemdoadadad_goods.txt",
        r"chem_goods.txt",
        r"chemodaaas_goods.txt",
        r"chchch_goods.txt",
        r"chemodan_goods (12).txt",
    ],
    "FAS": [
        r"FASOL_goods (2).txt",
    ],
    "DOL": [
        r"dollar_goods.txt",
        r"doll_goods.txt",
        r"dollar1_goods.txt",
        r"dollars_goods.txt",
        r"dollllar_goods.txt",
        r"dolor_goods.txt",
        r"dolor1_goods.txt",
        r"dolor3_goods.txt",
        r"dolllee_goods.txt",
    ],
}

OUT_DIR = Path("output")
LOGIN_RE = re.compile(r"^([^:\s]+):")
PURCHASED_RE = re.compile(r"^purchased=.*$")
GAMES_PURCHASED_RE = re.compile(r"^games_purchased=\[.*\]$")


def extract_login(line: str) -> str:
    match = LOGIN_RE.match(line.strip())
    return match.group(1) if match else ""


def split_line(line: str) -> Tuple[str, str]:
    if " | " in line:
        left, right = line.split(" | ", 1)
        return left.strip(), right.strip()
    return line.strip(), ""


def redact_email_password(left_part: str) -> str:
    """
    left_part ожидается в формате: login:...:email:password
    Заменяем email и password на REDACTED, сохраняя структуру.
    """
    parts = left_part.split(":")
    if len(parts) >= 4:
        parts[-2] = "REDACTED"
        parts[-1] = "REDACTED"
    return ":".join(parts)


def split_right_fields(right: str) -> List[str]:
    if not right:
        return []
    return [field.strip() for field in right.split("/") if field.strip()]


def build_no_purchases_right(right: str) -> str:
    fields = split_right_fields(right)
    filtered = [
        field
        for field in fields
        if not PURCHASED_RE.match(field) and not GAMES_PURCHASED_RE.match(field)
    ]
    return "/".join(filtered)


def build_with_purchases_right(right: str) -> str:
    # Оставляем поля как есть, даже если purchased/games_purchased отсутствуют.
    return "/".join(split_right_fields(right))


def format_output_line(redacted_left: str, right: str) -> str:
    return f"{redacted_left} | {right}" if right else redacted_left


def read_lines(paths: Iterable[str]) -> List[str]:
    result: List[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            print(f"[WARN] Файл не найден, пропускаю: {raw_path}")
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            if line:
                result.append(line)
    return result


def dedup_keep_last(lines: List[str]) -> Tuple[List[str], int, int]:
    logins = [extract_login(line) for line in lines]
    counts = Counter(login for login in logins if login)
    repeated_login_count = sum(1 for c in counts.values() if c > 1)

    seen = set()
    kept_reversed: List[str] = []

    for line in reversed(lines):
        login = extract_login(line)
        if not login:
            continue
        if login in seen:
            continue
        seen.add(login)
        kept_reversed.append(line)

    kept = list(reversed(kept_reversed))
    removed = len(lines) - len(kept)
    return kept, removed, repeated_login_count


def write_group(group: str, input_files: List[str]) -> None:
    lines = read_lines(input_files)
    total_in = len(lines)

    unique_lines, removed, repeated_login_count = dedup_keep_last(lines)
    total_out = len(unique_lines)

    out_group_dir = OUT_DIR / group
    out_group_dir.mkdir(parents=True, exist_ok=True)

    no_purchases_path = out_group_dir / f"{group}_no_purchases.txt"
    with_purchases_path = out_group_dir / f"{group}_with_purchases.txt"

    out_no: List[str] = []
    out_with: List[str] = []

    for raw in unique_lines:
        left, right = split_line(raw)
        redacted_left = redact_email_password(left)

        no_right = build_no_purchases_right(right)
        with_right = build_with_purchases_right(right)

        out_no.append(format_output_line(redacted_left, no_right))
        out_with.append(format_output_line(redacted_left, with_right))

    no_purchases_path.write_text(
        "\n".join(out_no) + ("\n" if out_no else ""),
        encoding="utf-8",
    )
    with_purchases_path.write_text(
        "\n".join(out_with) + ("\n" if out_with else ""),
        encoding="utf-8",
    )

    zip_path = OUT_DIR / f"{group}_PACK.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(no_purchases_path, arcname=no_purchases_path.name)
        archive.write(with_purchases_path, arcname=with_purchases_path.name)

    print(f"[{group}] входных строк: {total_in}")
    print(f"[{group}] уникальных логинов: {total_out}")
    print(f"[{group}] удалено строк (дубликаты по login): {removed}")
    print(f"[{group}] логинов с повторами: {repeated_login_count}")
    print(f"[{group}] выход: {no_purchases_path} | {with_purchases_path}")
    print(f"[{group}] zip: {zip_path}")
    print("-" * 50)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for group, files in GROUPS.items():
        write_group(group, files)


if __name__ == "__main__":
    main()
