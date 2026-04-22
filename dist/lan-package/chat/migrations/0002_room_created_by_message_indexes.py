from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_rooms',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['room', 'timestamp'], name='chat_messag_room_id_a07995_idx'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['timestamp'], name='chat_messag_timesta_54d6d5_idx'),
        ),
    ]
