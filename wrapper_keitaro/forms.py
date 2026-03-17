from django import forms


class CampaignCreateForm(forms.Form):
    name = forms.CharField(max_length=255, label='Campaign Name')
    geo = forms.CharField(max_length=10, label='Geo (country code)', initial='AU')
    offer_id = forms.IntegerField(label='Offer ID', min_value=1)

    def clean_offer_id(self):
        offer_id = self.cleaned_data['offer_id']
        # Можно проверить существование оффера через API (но для простоты пропустим)
        return offer_id