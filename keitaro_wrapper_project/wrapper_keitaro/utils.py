from django.db import transaction


@transaction.atomic
def recalculate_stream_weights(stream):
    """
    Пересчёт весов активных офферов в потоке с учётом закреплённых.
    """
    active_offers = stream.offers.filter(is_active=True).select_for_update()
    pinned = active_offers.filter(pinned=True)
    unpinned = active_offers.filter(pinned=False)

    sum_pinned = sum(o.weight for o in pinned)
    if sum_pinned > 100:
        raise ValueError("Sum of pinned weights exceeds 100")

    count_unpinned = unpinned.count()
    if count_unpinned == 0:
        if sum_pinned != 100:
            # Если нет unpinned, то pinned должны в сумме давать 100
            raise ValueError("Pinned offers must sum to 100 when no unpinned offers")
        return

    remaining = 100 - sum_pinned
    if remaining < 0:
        raise ValueError("Pinned weights exceed 100")
    if remaining == 0:
        # Все вес ушёл на pinned, unpinned получают 0
        for offer in unpinned:
            offer.weight = 0
            offer.save()
        return

    base = remaining // count_unpinned
    remainder = remaining % count_unpinned
    for i, offer in enumerate(unpinned):
        offer.weight = base + (1 if i < remainder else 0)
        offer.save()