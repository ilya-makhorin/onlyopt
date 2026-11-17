import asyncio
from decimal import ROUND_FLOOR, Decimal

OWN_SELLER = "myshop"
MAX_DELIVERY_DAYS = 6
DISCOUNT = Decimal("0.015")
MAX_DEVIATION = Decimal("0.30")
CENT = Decimal("0.01")


def _result(price, decision, reason):
    return {"price": price, "decision": decision, "reason": reason}


def _is_suitable(offer):
    days = offer["delivery_days"]
    if days is None or days > MAX_DELIVERY_DAYS:
        return False
    return offer["seller"].casefold() != OWN_SELLER


async def recommend_price(fetch_offers, current_price, min_price, timeout_s=2.0):
    try:
        result = await asyncio.wait_for(fetch_offers(), timeout=timeout_s)
    except asyncio.TimeoutError:
        return _result(current_price, "HOLD", f"Источник не ответил за {timeout_s} с")
    except Exception as exc:
        return _result(
            current_price, "HOLD", f"Ошибка источника: {type(exc).__name__}"
        )

    status = result.get("status")
    if status != "success":
        return _result(current_price, "HOLD", f"Статус источника: {status}")

    prices = [o["price"] for o in result.get("offers", []) if _is_suitable(o)]

    if not prices:
        return _result(current_price, "HOLD", "Нет подходящих предложений конкурентов")

    best = min(prices)
    undercut = (best * (1 - DISCOUNT)).quantize(CENT, rounding=ROUND_FLOOR)
    recommendation = max(undercut, min_price)
    if recommendation == min_price and undercut < min_price:
        basis = f"ограничено min_price {min_price}"
    else:
        basis = f"мин. цена конкурента {best} − 1,5%"

    if abs(recommendation - current_price) > MAX_DEVIATION * current_price:
        return _result(
            recommendation,
            "REVIEW",
            f"Отклонение от текущей цены больше 30% ({basis}); нужна ручная проверка",
        )
    return _result(recommendation, "APPLY", basis)


async def sample_fetch_offers():
    return {
        "status": "success",
        "offers": [
            {"seller": "myshop", "price": Decimal("4300.00"), "delivery_days": 2},
            {"seller": "PARTS", "price": Decimal("4800.00"), "delivery_days": 3},
            {"seller": "SLOW", "price": Decimal("4700.00"), "delivery_days": 8},
        ],
    }


if __name__ == "__main__":
    print(asyncio.run(recommend_price(
        sample_fetch_offers,
        current_price=Decimal("4900.00"),
        min_price=Decimal("4500.00"),
    )))
