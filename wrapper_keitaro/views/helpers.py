from ..models import StreamOffer
from ..keitaro_client import KeitaroClient


def get_stream_data(stream):
    """
    Формирует словарь с данными потока для JSON-ответа.
    Используется в API-эндпоинтах.
    """
    offers = []
    for so in stream.offers.select_related('offer').all():
        offers.append({
            'id': so.id,
            'offer_id': so.offer.keitaro_id,
            'offer_name': so.offer.name,
            'weight': so.weight,
            'pinned': so.pinned,
            'is_active': so.is_active,
            'synced': so.synced,
        })
    return {'id': stream.id, 'offers': offers}


def push_stream_to_keitaro(stream):
    """
    Отправляет текущее состояние потока (активные офферы) в Keitaro.
    Возвращает (True, None) при успехе или (False, error_message) при ошибке.
    """
    client = KeitaroClient()
    try:
        # Получаем актуальные данные потока из Keitaro (чтобы не потерять другие поля)
        stream_data = client.get_stream(stream.keitaro_id)
    except Exception as e:
        return False, f"Failed to get stream from Keitaro: {e}"

    # Формируем список активных офферов в формате API
    active_offers = []
    for so in stream.offers.filter(is_active=True).select_related('offer'):
        active_offers.append({
            'offer_id': so.offer.keitaro_id,
            'share': so.weight,
            'state': 'active'
        })
    stream_data['offers'] = active_offers

    try:
        client.update_stream(stream.keitaro_id, stream_data)
    except Exception as e:
        return False, f"Failed to update stream in Keitaro: {e}"

    # Помечаем все активные офферы как синхронизированные
    stream.offers.filter(is_active=True).update(synced=True)
    stream.offers.filter(is_active=False).update(synced=False)
    return True, None


def get_group_id(client, group_name, group_id_from_settings):
    """
    Возвращает ID группы.
    Если group_id_from_settings задан, используется он.
    Иначе ищет группу по имени group_name через client.
    Возвращает ID или выбрасывает исключение с сообщением об ошибке.
    """
    if group_id_from_settings:
        try:
            return int(group_id_from_settings)
        except ValueError:
            raise ValueError("DEFAULT_GROUP_ID must be an integer")
    else:
        groups = client.get_groups()
        group = next((g for g in groups if g['name'] == group_name), None)
        if not group:
            raise ValueError(f"Group '{group_name}' not found in Keitaro")
        return group['id']


def get_source_id(client, source_name, source_id_from_settings):
    """
    Возвращает ID источника.
    Если source_id_from_settings задан, используется он.
    Иначе ищет источник по имени или коду через client.
    Возвращает ID или выбрасывает исключение с сообщением об ошибке.
    """
    if source_id_from_settings:
        try:
            return int(source_id_from_settings)
        except ValueError:
            raise ValueError("DEFAULT_SOURCE_ID must be an integer")
    else:
        sources = client.get_sources()
        # Ищем по name или code
        source = next((s for s in sources if s.get('name') == source_name or s.get('code') == source_name), None)
        if not source:
            raise ValueError(f"Source '{source_name}' not found in Keitaro")
        return source['id']


def get_domain_id(client, domain_name, domain_id_from_settings):
    """
    Возвращает ID домена (опционально).
    Если domain_id_from_settings задан, используется он.
    Иначе ищет домен по имени domain_name через client.
    Возвращает ID или None, если домен не найден (это не ошибка).
    """
    if domain_id_from_settings:
        try:
            return int(domain_id_from_settings)
        except ValueError:
            raise ValueError("DEFAULT_DOMAIN_ID must be an integer")
    elif domain_name and domain_name != 'https://in.posdk.xyz/':
        try:
            domains = client.get_domains()
            domain = next((d for d in domains if d['name'] == domain_name), None)
            return domain['id'] if domain else None
        except Exception:
            return None
    return None