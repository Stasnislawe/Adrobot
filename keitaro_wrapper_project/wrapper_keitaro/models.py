from django.db import models


class Campaign(models.Model):
    keitaro_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    geo = models.CharField(max_length=10)
    domain = models.CharField(max_length=255)
    group = models.CharField(max_length=255)
    source = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Stream(models.Model):
    STREAM_TYPES = (
        ('google', 'Google Redirect'),
        ('offer', 'Offer Stream'),
    )
    keitaro_id = models.IntegerField()
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='streams')
    name = models.CharField(max_length=255, blank=True)
    stream_type = models.CharField(max_length=10, choices=STREAM_TYPES, default='offer')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('keitaro_id', 'campaign')

    def __str__(self):
        return f"{self.campaign.name} - {self.name or self.stream_type}"


class Offer(models.Model):
    keitaro_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.keitaro_id})"


class StreamOffer(models.Model):
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='offers')
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    weight = models.PositiveSmallIntegerField(default=0)
    pinned = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    synced = models.BooleanField(default=False)  # соответствует Keitaro?
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('stream', 'offer')

    def __str__(self):
        return f"{self.offer.name} - {self.weight}%"