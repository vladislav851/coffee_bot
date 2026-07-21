import re
from dataclasses import dataclass

_MOVEMENT_RE = re.compile(
    r"^(.+?)\s*-?\s*([\d]+(?:[.,]\d+)?)\s*(\S+)?\s*$"
)

_INVENTORY_RE = re.compile(
    r"^(.+?)\s+([\d]+(?:[.,]\d+)?)\s*$"
)


@dataclass
class MovementItem:
    raw_name: str
    quantity: float
    unit: str | None


@dataclass
class InventoryItem:
    raw_name: str
    quantity: float


def parse_movement(text: str) -> tuple[list[MovementItem], list[str]]:
    """Разбирает сообщение на позиции перемещения и нераспознанные строки."""
    items: list[MovementItem] = []
    errors: list[str] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _MOVEMENT_RE.match(line)
        if m:
            quantity = float(m.group(2).replace(",", "."))
            items.append(MovementItem(
                raw_name=m.group(1).strip(),
                quantity=quantity,
                unit=m.group(3),
            ))
        else:
            errors.append(line)

    return items, errors


def parse_inventory(text: str) -> tuple[list[InventoryItem], list[str]]:
    items: list[InventoryItem] = []
    errors: list[str] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _INVENTORY_RE.match(line)
        if m:
            quantity = float(m.group(2).replace(",", "."))
            items.append(InventoryItem(
                raw_name=m.group(1).strip(),
                quantity=quantity,
            ))
        else:
            errors.append(line)

    return items, errors


def split_names(text: str) -> list[str]:
    parts = re.split(r"[,\n]", text)
    return [p.strip() for p in parts if p.strip()]
