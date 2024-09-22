from django.db import models
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
        help_text="Date of the holiday. For non-recurring holidays only."
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
    recurring_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="The month (1-12) when the holiday recurs. Required for recurring holidays."
    )
    recurring_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="The day (1-31) when the holiday recurs. Required for recurring holidays."
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
        return f"{self.name} ({self.date})" if self.date else f"{self.name} (Recurring on {self.recurring_month}/{self.recurring_day})"

    def clean(self):
        # Non-recurring holiday must have a date
        if not self.is_recurring and not self.date:
            raise ValidationError("Non-recurring holidays must have a date.")
        
        # Recurring holiday must have a month and day but no date
        if self.is_recurring:
            if not self.recurring_month or not self.recurring_day:
                raise ValidationError("Recurring holidays must have both a month and a day.")
            if self.date:
                raise ValidationError("Recurring holidays should not have a specific date.")

        super().clean()

    def save(self, *args, **kwargs):
        # Ensure the holiday passes validation before saving
        self.full_clean()
        super().save(*args, **kwargs)
