import re
from datetime import datetime

import requests
from django.conf import settings


class KeitaroClient:
    def __init__(self):
        self.base_url = settings.KEITARO_API_URL.rstrip('/')
        self.api_key = settings.KEITARO_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            'Api-Key': self.api_key,
            'Content-Type': 'application/json',
        })

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            error_body = resp.text if hasattr(resp, 'text') else 'No body'
            raise Exception(f"Keitaro API error: {e} - Response body: {error_body}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Keitaro API error: {e}")

    # ---------- Справочники ----------
    def get_groups(self, group_type='campaign'):
        """Получить список групп кампаний. По умолчанию type=campaign."""
        return self._request('GET', '/groups', params={'type': group_type})

    def get_sources(self):
        """Получить список источников трафика"""
        return self._request('GET', '/traffic_sources')

    def get_domains(self):
        """Получить список доменов"""
        return self._request('GET', '/domains')

    # ---------- Кампании ----------
    def create_campaign(self, name, group_id, source_id, domain_id=None):
        """
        Создание кампании.
        group_id, source_id — обязательные числовые ID.
        domain_id — опционально.
        """
        # Генерируем alias из имени (транслитерация, удаление спецсимволов)
        base_alias = re.sub(r'[^a-zA-Z0-9_-]', '', name.replace(' ', '_'))
        # Добавляем временную метку для уникальности
        alias = f"{base_alias}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        data = {
            'name': name,
            'alias': alias,
            'group_id': group_id,
            'traffic_source_id': source_id,
            'type': 'position',
            'state': 'active',
            'cost_type': 'CPC',
            'cost_currency': 'USD',
            'cost_value': 0,
        }
        if domain_id:
            data['domain_id'] = domain_id
        return self._request('POST', '/campaigns', json=data)

    def get_campaign(self, campaign_id):
        return self._request('GET', f'/campaigns/{campaign_id}')

    # ---------- Потоки ----------
    def create_google_stream(self, campaign_id, geo):
        """Создание потока с редиректом на Google для указанной страны"""
        data = {
            'campaign_id': campaign_id,
            'name': f'{geo} → Google',
            'type': 'regular',
            'action_type': 'http',
            'action_options': {'url': 'https://google.com'},
            'filters': [
                {
                    'name': 'country',
                    'mode': 'accept',
                    'payload': [geo]
                }
            ],
            'state': 'active',
            'schema': 'redirect',  # для редиректа
        }
        return self._request('POST', '/streams', json=data)

    def create_offer_stream(self, campaign_id, offers):
        """
        Создание потока с офферами.
        offers: список словарей [{'offer_id': id, 'share': weight}, ...]
        """
        offers_api = [{'offer_id': o['offer_id'], 'share': o['share'], 'state': 'active'} for o in offers]
        data = {
            'campaign_id': campaign_id,
            'name': 'Main Offer Stream',
            'type': 'regular',
            'action_type': 'campaign',
            'offers': offers_api,
            'state': 'active',
            'schema': 'landings',  # для офферов, согласно документации
        }
        return self._request('POST', '/streams', json=data)

    def get_campaign_streams(self, campaign_id):
        """Получение всех потоков кампании"""
        return self._request('GET', f'/campaigns/{campaign_id}/streams')

    def update_stream_offers(self, stream_id, offers):
        """
        Обновление офферов в потоке.
        offers: список [{'offer_id': id, 'share': weight}, ...]
        """
        # В Keitaro поток обновляется целиком, поэтому отправляем всё нужное
        # Но для простоты будем обновлять только offers
        # Сначала получим текущий поток, чтобы сохранить остальные поля
        stream = self._request('GET', f'/streams/{stream_id}')
        stream['offers'] = offers
        return self._request('PUT', f'/streams/{stream_id}', json=stream)

    def get_stream(self, stream_id):
        """Получение потока по ID"""
        return self._request('GET', f'/streams/{stream_id}')

    def update_stream(self, stream_id, data):
        """Полное обновление потока"""
        return self._request('PUT', f'/streams/{stream_id}', json=data)

    # ---------- Офферы ----------
    def search_offers(self, query):
        return self._request('GET', '/offers', params={'search': query})

    def get_offer(self, offer_id):
        return self._request('GET', f'/offers/{offer_id}')