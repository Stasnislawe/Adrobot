import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.shortcuts import get_object_or_404

from ..models import Campaign, Stream, Offer, StreamOffer
from ..keitaro_client import KeitaroClient
from ..utils import recalculate_stream_weights
from .helpers import get_stream_data, push_stream_to_keitaro


@require_http_methods(["GET"])
def api_campaign_streams(request, campaign_id):
    """
    Возвращает JSON со всеми потоками и их офферами для указанной кампании.
    Используется для первоначальной загрузки и обновления интерфейса.
    """
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    data = []
    for stream in campaign.streams.all():
        stream_data = {
            'id': stream.id,
            'keitaro_id': stream.keitaro_id,
            'name': stream.name,
            'stream_type': stream.stream_type,
            'offers': []
        }
        for so in stream.offers.select_related('offer').all():
            stream_data['offers'].append({
                'id': so.id,
                'offer_id': so.offer.keitaro_id,
                'offer_name': so.offer.name,
                'weight': so.weight,
                'pinned': so.pinned,
                'is_active': so.is_active,
                'synced': so.synced,
            })
        data.append(stream_data)
    return JsonResponse(data, safe=False)


@require_POST
def api_fetch_streams(request, campaign_id):
    """
    Загружает актуальные данные потоков из Keitaro и обновляет локальную БД.
    Применяется при нажатии кнопки "Fetch Streams".
    """
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    client = KeitaroClient()
    try:
        streams_data = client.get_campaign_streams(campaign.keitaro_id)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    for s_data in streams_data:
        # Получаем или создаём поток
        stream, _ = Stream.objects.get_or_create(
            keitaro_id=s_data['id'],
            campaign=campaign,
            defaults={
                'name': s_data.get('name', ''),
                'stream_type': 'offer' if s_data['action_type'] == 'campaign' else 'google'
            }
        )
        # Обновляем имя и тип, если изменились
        stream.name = s_data.get('name', stream.name)
        stream.stream_type = 'offer' if s_data['action_type'] == 'campaign' else 'google'
        stream.save()

        # Если поток с офферами
        if s_data['action_type'] == 'campaign':
            # Словарь офферов из Keitaro {offer_id: share}
            keitaro_offers = {o['offer_id']: o.get('share', 0) for o in s_data.get('offers', [])}

            # Помечаем все существующие связи как несинхронизированные
            stream.offers.update(synced=False)

            # Добавляем или обновляем офферы, присутствующие в Keitaro
            for oid, share in keitaro_offers.items():
                offer, _ = Offer.objects.get_or_create(keitaro_id=oid, defaults={'name': 'Unknown'})
                so, _ = StreamOffer.objects.get_or_create(stream=stream, offer=offer)
                so.weight = share
                so.is_active = True
                so.synced = True
                so.pinned = False  # при сбросе из Keitaro pinned сбрасывается
                so.save()

            # Оставшиеся (с synced=False) деактивируем
            stream.offers.filter(synced=False).update(is_active=False, synced=False)

    return JsonResponse({'status': 'ok'})


@require_POST
def api_cancel_changes(request, campaign_id):
    """
    Отменяет локальные изменения, сбрасывая состояние потоков до состояния в Keitaro.
    Соответствует кнопке "Cancel".
    """
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    client = KeitaroClient()
    try:
        streams_data = client.get_campaign_streams(campaign.keitaro_id)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    for s_data in streams_data:
        stream = Stream.objects.get(keitaro_id=s_data['id'], campaign=campaign)
        if s_data['action_type'] == 'campaign':
            keitaro_offers = {o['offer_id']: o.get('share', 0) for o in s_data.get('offers', [])}
            # Деактивируем все локальные офферы
            stream.offers.update(is_active=False, synced=False)
            # Активируем те, что есть в Keitaro
            for oid, share in keitaro_offers.items():
                offer = Offer.objects.get(keitaro_id=oid)
                so, _ = StreamOffer.objects.get_or_create(stream=stream, offer=offer)
                so.weight = share
                so.is_active = True
                so.synced = True
                so.pinned = False
                so.save()
    return JsonResponse({'status': 'ok'})


def api_search_offers(request):
    """
    Поиск офферов по запросу (для автокомплита).
    Возвращает список словарей с id, label и value.
    """
    query = request.GET.get('term', '')
    if not query:
        return JsonResponse([], safe=False)
    client = KeitaroClient()
    try:
        results = client.search_offers(query)
        items = [
            {'id': r['id'], 'label': f"{r['name']} ({r['id']})", 'value': r['name']}
            for r in results
        ]
        return JsonResponse(items, safe=False)
    except Exception:
        return JsonResponse([], safe=False)


@require_POST
def api_add_offer(request, stream_id):
    """
    Добавляет оффер в поток и синхронизирует с Keitaro.
    Ожидает JSON: {"offer_id": 123}
    """
    stream = get_object_or_404(Stream, pk=stream_id)
    try:
        data = json.loads(request.body)
        offer_id = data.get('offer_id')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not offer_id:
        return JsonResponse({'error': 'offer_id required'}, status=400)

    client = KeitaroClient()
    offer, created = Offer.objects.get_or_create(keitaro_id=offer_id, defaults={'name': 'Unknown'})
    if created:
        try:
            offer_data = client.get_offer(offer_id)
            offer.name = offer_data.get('name', 'Unknown')
            offer.save()
        except Exception:
            pass

    so, created = StreamOffer.objects.get_or_create(
        stream=stream, offer=offer,
        defaults={'weight': 0, 'synced': False, 'is_active': True}
    )
    if not created and not so.is_active:
        # Ранее удалённый оффер — восстанавливаем
        so.is_active = True
        so.synced = False
        so.pinned = False
        so.save()
    elif not created and so.is_active:
        return JsonResponse({'error': 'Offer already active in this stream'}, status=400)

    recalculate_stream_weights(stream)

    success, error = push_stream_to_keitaro(stream)
    if not success:
        return JsonResponse({'error': error}, status=500)

    return JsonResponse(get_stream_data(stream))


@require_POST
def api_remove_offer(request, stream_offer_id):
    """
    Мягко удаляет оффер из потока (деактивирует) и синхронизирует с Keitaro.
    """
    so = get_object_or_404(StreamOffer, pk=stream_offer_id)
    stream = so.stream
    so.is_active = False
    so.synced = False
    so.pinned = False
    so.save()
    recalculate_stream_weights(stream)

    success, error = push_stream_to_keitaro(stream)
    if not success:
        return JsonResponse({'error': error}, status=500)

    return JsonResponse(get_stream_data(stream))


@require_POST
def api_restore_offer(request, stream_offer_id):
    """
    Восстанавливает ранее удалённый (деактивированный) оффер в потоке.
    """
    so = get_object_or_404(StreamOffer, pk=stream_offer_id)
    stream = so.stream
    so.is_active = True
    so.synced = False
    so.save()
    recalculate_stream_weights(stream)

    success, error = push_stream_to_keitaro(stream)
    if not success:
        return JsonResponse({'error': error}, status=500)

    return JsonResponse(get_stream_data(stream))


@require_POST
def api_pin_offer(request, stream_offer_id):
    """
    Закрепляет (pinned) или открепляет вес оффера.
    Переключает состояние pinned.
    """
    so = get_object_or_404(StreamOffer, pk=stream_offer_id)
    stream = so.stream
    so.pinned = not so.pinned
    so.synced = False
    so.save()
    recalculate_stream_weights(stream)

    success, error = push_stream_to_keitaro(stream)
    if not success:
        return JsonResponse({'error': error}, status=500)

    return JsonResponse(get_stream_data(stream))


@require_POST
def api_push_streams(request, campaign_id):
    """
    Принудительно отправляет все потоки кампании (с офферами) в Keitaro.
    Используется при нажатии кнопки "Push".
    """
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    for stream in campaign.streams.filter(stream_type='offer'):
        success, error = push_stream_to_keitaro(stream)
        if not success:
            return JsonResponse({'error': f"Stream {stream.id}: {error}"}, status=500)
    return JsonResponse({'status': 'ok'})