# Generated migration for GlossaryTerm model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worldinfo', '0003_news_alter_worldinfopage_options_maplocation'),
    ]

    operations = [
        migrations.CreateModel(
            name='GlossaryTerm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('term', models.CharField(db_index=True, help_text="The term to highlight (e.g., 'Westelth', 'The Empire')", max_length=200, unique=True)),
                ('short_description', models.TextField(help_text='Brief description shown in the popover (max 500 characters)', max_length=500)),
                ('link_url', models.CharField(blank=True, help_text='Optional URL to full page (e.g., /world/westelth/ or /wiki/empire/)', max_length=500)),
                ('link_text', models.CharField(blank=True, default='Learn more', help_text="Text for the 'Learn more' link (default: 'Learn more')", max_length=100)),
                ('is_active', models.BooleanField(default=True, help_text='Uncheck to temporarily disable highlighting for this term')),
                ('case_sensitive', models.BooleanField(default=False, help_text='Check if the term should be matched case-sensitively')),
                ('priority', models.IntegerField(default=0, help_text='Higher priority terms are matched first (useful for overlapping terms)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Glossary Term',
                'verbose_name_plural': 'Glossary Terms',
                'ordering': ['-priority', 'term'],
            },
        ),
    ]

