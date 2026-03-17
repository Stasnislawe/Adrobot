from django.urls import path
from .views import html_views, api_views

urlpatterns = [
    path('', html_views.CampaignListView.as_view(), name='campaign_list'),
    path('new/', html_views.campaign_create, name='campaign_create'),
    path('campaign/<int:campaign_id>/', html_views.campaign_detail, name='campaign_detail'),

    # API endpoints
    path('api/campaigns/<int:campaign_id>/streams/', api_views.api_campaign_streams, name='api_campaign_streams'),
    path('api/streams/<int:stream_id>/add_offer/', api_views.api_add_offer, name='api_add_offer'),
    path('api/stream-offers/<int:stream_offer_id>/remove/', api_views.api_remove_offer, name='api_remove_offer'),
    path('api/stream-offers/<int:stream_offer_id>/restore/', api_views.api_restore_offer, name='api_restore_offer'),
    path('api/stream-offers/<int:stream_offer_id>/pin/', api_views.api_pin_offer, name='api_pin_offer'),
    path('api/campaigns/<int:campaign_id>/fetch/', api_views.api_fetch_streams, name='api_fetch_streams'),
    path('api/campaigns/<int:campaign_id>/push/', api_views.api_push_streams, name='api_push_streams'),
    path('api/campaigns/<int:campaign_id>/cancel/', api_views.api_cancel_changes, name='api_cancel_changes'),
    path('api/search_offers/', api_views.api_search_offers, name='api_search_offers'),
]