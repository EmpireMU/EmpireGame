# Generated migration for GlossaryTerm aliases field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worldinfo', '0007_glossaryterm'),
    ]

    operations = [
        migrations.AddField(
            model_name='glossaryterm',
            name='aliases',
            field=models.TextField(blank=True, help_text="Alternative terms that should show the same definition (one per line, e.g., 'Imperial House' for 'House Otrese', or 'Greytides' for 'Greytide')"),
        ),
    ]

