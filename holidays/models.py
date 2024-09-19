# holidays/models.py

from django.db import models
from django.utils import timezone
from datetime import date
from django.core.exceptions import ValidationError

class Holiday(models.Model):
    HOLIDAY_TYPE_CHOICES = [
        ('non_working', 'Non-Working Holiday'),
        ('special_non_working', 'Special Non-Working Holiday'),
    ]

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the holiday, e.g., New Year, Christmas."
    )
    date = models.DateField(
        null=True,        # Allow null values
        blank=True,       # Allow blank values in forms
        help_text="Date of the holiday."
    )
    is_recurring = models.BooleanField(
        default=False,
        help_text="Indicates if the holiday recurs annually."
    )
    holiday_type = models.CharField(
        max_length=20,
        choices=HOLIDAY_TYPE_CHOICES,
        default='non_working',
        help_text='Type of the holiday. "Non-Working" are paid even if not clocked in. "Special Non-Working" require clock-in for pay.'
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the holiday."
    )

    class Meta:
        ordering = ['date']
        verbose_name = "Holiday"
        verbose_name_plural = "Holidays"

    def __str__(self):
        return f"{self.name} ({self.date})" if self.date else f"{self.name} (Recurring)"

    def clean(self):
        if self.is_recurring and self.holiday_type not in ['non_working', 'special_non_working']:
            raise ValidationError("Recurring holidays must be either 'Non-Working' or 'Special Non-Working'.")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
