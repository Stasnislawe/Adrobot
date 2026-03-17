from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import ListView
from django.conf import settings

from ..models import Campaign, Stream, Offer, StreamOffer
from ..forms import CampaignCreateForm
from ..keitaro_client import KeitaroClient
from .helpers import get_group_id, get_source_id, get_domain_id


class CampaignListView(ListView):
    """Список всех кампаний."""
    model = Campaign
    template_name = 'keitaro_wrapper/campaign_list.html'
    context_object_name = 'campaigns'
    ordering = ['-created_at']


@ensure_csrf_cookie
def campaign_create(request):
    """
    Создание новой кампании.
    GET: отображает форму.
    POST: создаёт кампанию в Keitaro и локально.
    """
    if request.method == 'POST':
        form = CampaignCreateForm(request.POST)
        if form.is_valid():
            client = KeitaroClient()

            # --- Получение ID группы, источника и домена ---
            try:
                group_id = get_group_id(
                    client,
                    settings.DEFAULT_GROUP_NAME,
                    getattr(settings, 'DEFAULT_GROUP_ID', None)
                )
                source_id = get_source_id(
                    client,
                    settings.DEFAULT_SOURCE_NAME,
                    getattr(settings, 'DEFAULT_SOURCE_ID', None)
                )
                domain_id = get_domain_id(
                    client,
                    settings.DEFAULT_DOMAIN,
                    getattr(settings, 'DEFAULT_DOMAIN_ID', None)
                )
            except ValueError as e:
                messages.error(request, str(e))
                return render(request, 'keitaro_wrapper/campaign_create.html', {'form': form})
            except Exception as e:
                messages.error(request, f"Failed to fetch required data from Keitaro: {e}")
                return render(request, 'keitaro_wrapper/campaign_create.html', {'form': form})

            # --- Создание кампании в Keitaro ---
            try:
                camp_data = client.create_campaign(
                    name=form.cleaned_data['name'],
                    group_id=group_id,
                    source_id=source_id,
                    domain_id=domain_id
                )
            except Exception as e:
                messages.error(request, f"Failed to create campaign in Keitaro: {e}")
                return render(request, 'keitaro_wrapper/campaign_create.html', {'form': form})

            # --- Локальное сохранение кампании ---
            campaign = Campaign.objects.create(
                keitaro_id=camp_data['id'],
                name=form.cleaned_data['name'],
                geo=form.cleaned_data['geo'],
                domain=settings.DEFAULT_DOMAIN,
                group=settings.DEFAULT_GROUP_NAME,
                source=settings.DEFAULT_SOURCE_NAME
            )

            # --- Создание Google потока ---
            try:
                google_stream = client.create_google_stream(
                    campaign_id=campaign.keitaro_id,
                    geo=form.cleaned_data['geo']
                )
                Stream.objects.create(
                    keitaro_id=google_stream['id'],
                    campaign=campaign,
                    stream_type='google',
                    name=google_stream.get('name', 'Google Redirect')
                )
            except Exception as e:
                campaign.delete()
                messages.error(request, f"Failed to create Google stream: {e}")
                return render(request, 'keitaro_wrapper/campaign_create.html', {'form': form})

            # --- Создание потока с оффером ---
            try:
                offer_payload = [{'offer_id': form.cleaned_data['offer_id'], 'share': 100}]
                offer_stream = client.create_offer_stream(
                    campaign_id=campaign.keitaro_id,
                    offers=offer_payload
                )
                stream = Stream.objects.create(
                    keitaro_id=offer_stream['id'],
                    campaign=campaign,
                    stream_type='offer',
                    name=offer_stream.get('name', 'Main Offer')
                )
            except Exception as e:
                campaign.delete()  # В реальном проекте нужно удалить и Google поток из Keitaro
                messages.error(request, f"Failed to create offer stream: {e}")
                return render(request, 'keitaro_wrapper/campaign_create.html', {'form': form})

            # --- Сохранение оффера и связи ---
            offer, _ = Offer.objects.get_or_create(
                keitaro_id=form.cleaned_data['offer_id'],
                defaults={'name': 'Unknown'}
            )
            try:
                offer_data = client.get_offer(form.cleaned_data['offer_id'])
                offer.name = offer_data.get('name', 'Unknown')
                offer.save()
            except Exception:
                pass

            StreamOffer.objects.create(
                stream=stream,
                offer=offer,
                weight=100,
                synced=True
            )

            messages.success(request, "Campaign created successfully!")
            return redirect('campaign_detail', campaign_id=campaign.id)
    else:
        form = CampaignCreateForm()

    return render(request, 'keitaro_wrapper/campaign_create.html', {'form': form})


@ensure_csrf_cookie
def campaign_detail(request, campaign_id):
    """Детальная страница кампании с потоками и офферами."""
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    return render(request, 'keitaro_wrapper/campaign_detail.html', {'campaign': campaign})