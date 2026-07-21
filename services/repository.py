import json
from database.db import get_connection


async def get_all_products() -> dict[str, dict]:
    """Возвращает {нормализованное_имя: {id, display_name, unit}} для всех товаров."""
    conn = await get_connection()
    try:
        async with conn.execute(
            "SELECT id, name, display_name, unit FROM products"
        ) as cursor:
            rows = await cursor.fetchall()
    finally:
        await conn.close()

    return {
        row["name"]: {
            "id": row["id"],
            "display_name": row["display_name"],
            "unit": row["unit"],
        }
        for row in rows
    }


async def get_product_by_id(product_id: int) -> dict | None:
    conn = await get_connection()
    try:
        async with conn.execute(
            "SELECT id, name, display_name, unit FROM products WHERE id = ?",
            (product_id,),
        ) as cursor:
            row = await cursor.fetchone()
    finally:
        await conn.close()

    return dict(row) if row else None


async def get_stock(product_id: int, location: str) -> float:
    conn = await get_connection()
    try:
        async with conn.execute(
            "SELECT quantity FROM stock WHERE product_id = ? AND location = ?",
            (product_id, location),
        ) as cursor:
            row = await cursor.fetchone()
    finally:
        await conn.close()

    return row["quantity"] if row else 0.0


async def get_stock_many(product_ids: list[int], location: str) -> dict[int, float]:
    """Возвращает {product_id: quantity} для списка товаров."""
    if not product_ids:
        return {}

    placeholders = ",".join("?" * len(product_ids))
    conn = await get_connection()
    try:
        async with conn.execute(
            f"SELECT product_id, quantity FROM stock "
            f"WHERE product_id IN ({placeholders}) AND location = ?",
            (*product_ids, location),
        ) as cursor:
            rows = await cursor.fetchall()
    finally:
        await conn.close()

    return {row["product_id"]: row["quantity"] for row in rows}


async def get_full_stock_report() -> list[dict]:
    """
    Возвращает остатки по всем товарам на обеих локациях, сгруппированные по категориям.
    [{category_name, display_name, unit, warehouse_qty, coffee_qty}, ...]
    """
    conn = await get_connection()
    try:
        async with conn.execute(
            "SELECT COALESCE(c.name, 'Без категории') AS category_name, "
            "p.display_name, p.unit, "
            "COALESCE(sw.quantity, 0) AS warehouse_qty, "
            "COALESCE(sc.quantity, 0) AS coffee_qty "
            "FROM products p "
            "LEFT JOIN categories c ON p.category_id = c.id "
            "LEFT JOIN stock sw ON sw.product_id = p.id AND sw.location = 'warehouse' "
            "LEFT JOIN stock sc ON sc.product_id = p.id AND sc.location = 'coffee_shop' "
            "ORDER BY category_name, p.display_name"
        ) as cursor:
            rows = await cursor.fetchall()
    finally:
        await conn.close()

    return [dict(row) for row in rows]


async def get_stock_report_by_location(location: str) -> list[dict]:
    """
    Возвращает остатки по всем товарам на ОДНОЙ локации, сгруппированные по категориям.
    [{category_name, display_name, unit, quantity}, ...]
    """
    conn = await get_connection()
    try:
        async with conn.execute(
            "SELECT COALESCE(c.name, 'Без категории') AS category_name, "
            "p.display_name, p.unit, COALESCE(s.quantity, 0) AS quantity "
            "FROM products p "
            "LEFT JOIN categories c ON p.category_id = c.id "
            "LEFT JOIN stock s ON s.product_id = p.id AND s.location = ? "
            "ORDER BY category_name, p.display_name",
            (location,),
        ) as cursor:
            rows = await cursor.fetchall()
    finally:
        await conn.close()

    return [dict(row) for row in rows]


async def move_products(
    items: list[dict],
    from_location: str,
    to_location: str,
    user_id: int,
) -> dict:
    """
    Перемещает товары в одной транзакции.
    items — список {product_id, quantity}.
    Позиции, уводящие источник в минус, не применяются (попадают в "blocked").
    Возвращает {"moved": [...], "blocked": [...]}.
    """
    conn = await get_connection()
    moved = []
    blocked = []
    payload_items = []

    try:
        for item in items:
            pid = item["product_id"]
            qty = item["quantity"]

            async with conn.execute(
                "SELECT quantity FROM stock WHERE product_id = ? AND location = ?",
                (pid, from_location),
            ) as cur:
                row = await cur.fetchone()
            old_src = row["quantity"] if row else 0.0

            if old_src < qty:
                blocked.append({"product_id": pid, "quantity": qty, "available": old_src})
                continue

            async with conn.execute(
                "SELECT quantity FROM stock WHERE product_id = ? AND location = ?",
                (pid, to_location),
            ) as cur:
                row = await cur.fetchone()
            old_dst = row["quantity"] if row else 0.0

            new_src = old_src - qty
            new_dst = old_dst + qty

            await conn.execute(
                "INSERT INTO stock (product_id, location, quantity) VALUES (?, ?, ?) "
                "ON CONFLICT(product_id, location) DO UPDATE SET quantity = excluded.quantity",
                (pid, from_location, new_src),
            )
            await conn.execute(
                "INSERT INTO stock (product_id, location, quantity) VALUES (?, ?, ?) "
                "ON CONFLICT(product_id, location) DO UPDATE SET quantity = excluded.quantity",
                (pid, to_location, new_dst),
            )

            moved.append({"product_id": pid, "quantity": qty, "new_src_qty": new_src})
            payload_items.append({
                "product_id": pid,
                "from_location": from_location,
                "to_location": to_location,
                "old_src": old_src,
                "old_dst": old_dst,
            })

        if payload_items:
            await conn.execute(
                "INSERT INTO movement_log (telegram_user_id, action_type, payload) VALUES (?, ?, ?)",
                (user_id, "movement", json.dumps(payload_items)),
            )
        await conn.commit()
    finally:
        await conn.close()

    return {"moved": moved, "blocked": blocked}


async def set_stock(product_id: int, location: str, quantity: float, user_id: int) -> float:
    """Перезаписывает остаток. Возвращает старое значение (для лога отмены)."""
    conn = await get_connection()
    try:
        async with conn.execute(
            "SELECT quantity FROM stock WHERE product_id = ? AND location = ?",
            (product_id, location),
        ) as cur:
            row = await cur.fetchone()
        old_qty = row["quantity"] if row else 0.0

        await conn.execute(
            "INSERT INTO stock (product_id, location, quantity) VALUES (?, ?, ?) "
            "ON CONFLICT(product_id, location) DO UPDATE SET quantity = excluded.quantity",
            (product_id, location, quantity),
        )
        await conn.execute(
            "INSERT INTO movement_log (telegram_user_id, action_type, payload) VALUES (?, ?, ?)",
            (user_id, "inventory_adjust", json.dumps({
                "product_id": product_id,
                "location": location,
                "old_qty": old_qty,
                "new_qty": quantity,
            })),
        )
        await conn.commit()
    finally:
        await conn.close()

    return old_qty


async def get_all_product_info() -> dict[str, dict]:
    """Возвращает {нижний_регистр_имени: {display_name, calories, ...}}."""
    conn = await get_connection()
    try:
        async with conn.execute(
            "SELECT name, calories, protein, fat, carbs, description FROM product_info"
        ) as cursor:
            rows = await cursor.fetchall()
    finally:
        await conn.close()

    return {
        row["name"].lower(): dict(row)
        for row in rows
    }


async def get_user_direction(user_id: int) -> str:
    conn = await get_connection()
    try:
        async with conn.execute(
            "SELECT movement_direction FROM user_settings WHERE telegram_user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    finally:
        await conn.close()

    return row["movement_direction"] if row else "warehouse_to_coffee"


async def toggle_user_direction(user_id: int) -> str:
    """Переключает направление и возвращает новое значение."""
    current = await get_user_direction(user_id)
    new_direction = (
        "coffee_to_warehouse" if current == "warehouse_to_coffee" else "warehouse_to_coffee"
    )
    conn = await get_connection()
    try:
        await conn.execute(
            "INSERT INTO user_settings (telegram_user_id, movement_direction) VALUES (?, ?) "
            "ON CONFLICT(telegram_user_id) DO UPDATE SET movement_direction = excluded.movement_direction",
            (user_id, new_direction),
        )
        await conn.commit()
    finally:
        await conn.close()

    return new_direction


async def undo_last(user_id: int) -> dict | None:
    """
    Откатывает последнее действие пользователя.
    Возвращает словарь с описанием того, что отменили, или None если нечего отменять.
    """
    conn = await get_connection()
    try:
        async with conn.execute(
            "SELECT id, action_type, payload FROM movement_log "
            "WHERE telegram_user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()

        if not row:
            return None

        log_id = row["id"]
        action_type = row["action_type"]
        payload = json.loads(row["payload"])

        if action_type == "movement":
            for item in payload:
                await conn.execute(
                    "INSERT INTO stock (product_id, location, quantity) VALUES (?, ?, ?) "
                    "ON CONFLICT(product_id, location) DO UPDATE SET quantity = excluded.quantity",
                    (item["product_id"], item["from_location"], item["old_src"]),
                )
                await conn.execute(
                    "INSERT INTO stock (product_id, location, quantity) VALUES (?, ?, ?) "
                    "ON CONFLICT(product_id, location) DO UPDATE SET quantity = excluded.quantity",
                    (item["product_id"], item["to_location"], item["old_dst"]),
                )
        elif action_type == "inventory_adjust":
            await conn.execute(
                "INSERT INTO stock (product_id, location, quantity) VALUES (?, ?, ?) "
                "ON CONFLICT(product_id, location) DO UPDATE SET quantity = excluded.quantity",
                (payload["product_id"], payload["location"], payload["old_qty"]),
            )

        await conn.execute("DELETE FROM movement_log WHERE id = ?", (log_id,))
        await conn.commit()
    finally:
        await conn.close()

    return {"action_type": action_type, "payload": payload}
