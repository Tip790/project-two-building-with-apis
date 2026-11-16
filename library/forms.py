from django import forms

from .models import MAX_HOURS, LibraryEntry


class EntryForm(forms.ModelForm):
    """The owner's editable fields for one library entry."""

    class Meta:
        model = LibraryEntry
        fields = ["status", "rating", "hours_played", "platform", "notes"]
        labels = {"rating": "Rating (1–5 stars)", "hours_played": "Hours played"}
        help_texts = {
            "rating": "Leave blank for unrated.",
            "hours_played": "Leave blank if you haven't tracked it.",
        }
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5, "step": 1}),
            "hours_played": forms.NumberInput(
                attrs={"min": 0, "max": MAX_HOURS, "step": "0.1"}
            ),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only offer this game's platforms. The field still accepts any
        # platform, so a foreign one reaches the shared validator in
        # LibraryEntry.clean() and gets the same message the API gives.
        platform = self.fields["platform"]
        platform.empty_label = "Not set"
        platform.widget.choices = [("", "Not set")] + [
            (p.pk, p.name) for p in self.instance.game.platforms.all()
        ]
