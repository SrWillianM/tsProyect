import mimetypes
import os

from .models import Message, Room


def serialize_message(message, source="live"):
    payload = {
        "id": message.id,
        "alias": message.alias,
        "message": message.content,
        "timestamp": message.timestamp.isoformat(),
        "source": source,
    }

    if message.attachment:
        attachment_mime = message.attachment_mime or mimetypes.guess_type(
            message.attachment.name
        )[0]
        payload.update(
            {
                "attachment_url": message.attachment.url,
                "attachment_name": message.attachment_name
                or os.path.basename(message.attachment.name),
                "attachment_mime": attachment_mime or "",
                "attachment_is_image": bool(
                    attachment_mime and attachment_mime.startswith("image/")
                ),
            }
        )

    if message.sticker and message.sticker.image:
        payload.update(
            {
                "sticker_id": message.sticker_id,
                "sticker_name": message.sticker.name,
                "sticker_url": message.sticker.image.url,
            }
        )

    return payload


def create_message_payload(
    room_name,
    alias,
    content="",
    attachment=None,
    attachment_name="",
    attachment_mime="",
    sticker=None,
):
    room, _ = Room.objects.get_or_create(name=room_name)
    message = Message.objects.create(
        room=room,
        alias=alias,
        content=content,
        attachment=attachment,
        attachment_name=attachment_name,
        attachment_mime=attachment_mime,
        sticker=sticker,
    )
    return serialize_message(message)
