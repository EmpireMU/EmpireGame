# Generated by Django 4.2.21 on 2025-07-13 21:13

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="WorldInfoPage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=200, unique=True)),
                (
                    "content",
                    models.TextField(
                        help_text="Use Markdown formatting. Use [[Character Name]] to link to characters."
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        blank=True,
                        help_text="e.g., Factions, History, Locations, NPCs",
                        max_length=50,
                    ),
                ),
                (
                    "subcategory",
                    models.CharField(
                        blank=True,
                        help_text="e.g., Realm of Dyria, Imperial Territories",
                        max_length=50,
                    ),
                ),
                (
                    "is_public",
                    models.BooleanField(
                        default=True, help_text="Uncheck to make this page GM-only"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["category", "subcategory", "title"],
            },
        ),
    ]
