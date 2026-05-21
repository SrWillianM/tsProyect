import json

from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from channels.layers import get_channel_layer

from .forms import ProfileForm, RoomCreateForm, SignUpForm
from .message_utils import create_message_payload, serialize_message
from .models import ChannelKind, Profile, Room, Sticker, default_nickname


def _rooms_by_kind():
    rooms = Room.objects.only("id", "name", "kind").order_by("kind", "name")
    return {
        ChannelKind.CHAT: list(rooms.filter(kind=ChannelKind.CHAT)),
        ChannelKind.VOICE: list(rooms.filter(kind=ChannelKind.VOICE)),
    }


def _ensure_profile(user):
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={"nickname": default_nickname(user)},
    )
    if not profile.nickname:
        profile.nickname = default_nickname(user)
        profile.save(update_fields=["nickname"])
    return profile


@login_required
def index(request):
    profile = _ensure_profile(request.user)
    rooms_by_kind = _rooms_by_kind()
    return render(
        request,
        "chat/index.html",
        {
            "chat_rooms": rooms_by_kind[ChannelKind.CHAT],
            "voice_rooms": rooms_by_kind[ChannelKind.VOICE],
            "profile": profile,
            "room_form": RoomCreateForm(),
        },
    )


@login_required
def room(request, room_name):
    room = get_object_or_404(Room, name=room_name)
    profile = _ensure_profile(request.user)
    rooms_by_kind = _rooms_by_kind()
    return render(
        request,
        "chat/room.html",
        {
            "room": room,
            "room_name": room_name,
            "chat_rooms": rooms_by_kind[ChannelKind.CHAT],
            "voice_rooms": rooms_by_kind[ChannelKind.VOICE],
            "profile": profile,
            "display_name": profile.nickname,
            "is_voice_room": room.kind == ChannelKind.VOICE,
            "webrtc_ice_servers": settings.WEBRTC_ICE_SERVERS,
        },
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("chat-index")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Sesión iniciada.")
        return redirect("chat-index")

    return render(request, "registration/login.html", {"form": form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("chat-index")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        _ensure_profile(user)
        login(request, user)
        messages.success(request, "Cuenta creada correctamente.")
        return redirect("chat-index")

    return render(request, "registration/signup.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    profile = _ensure_profile(request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=profile)

    rooms_by_kind = _rooms_by_kind()
    return render(
        request,
        "chat/profile.html",
        {
            "form": form,
            "profile": profile,
            "chat_rooms": rooms_by_kind[ChannelKind.CHAT],
            "voice_rooms": rooms_by_kind[ChannelKind.VOICE],
        },
    )


@login_required
@require_http_methods(["POST"])
def create_room(request):
    form = RoomCreateForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revisa el nombre y el tipo del canal.")
        return redirect("chat-index")

    room = form.save(commit=False)
    room.created_by = request.user
    room.save()
    return redirect("chat-room", room_name=room.name)


def _parse_pagination(query_dict):
    try:
        limit = int(query_dict.get("limit", 30))
        offset = int(query_dict.get("offset", 0))
    except (TypeError, ValueError):
        return None, None

    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return limit, offset


def _parse_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@require_http_methods(["GET", "POST"])
def api_rooms(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    if request.method == "GET":
        rooms = list(
            Room.objects.only("id", "name", "kind", "created_at").values(
                "id", "name", "kind", "created_at"
            )
        )
        return JsonResponse({"rooms": rooms})

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    name = (payload.get("name") or "").strip()[:100]
    kind = (payload.get("kind") or ChannelKind.CHAT).strip()
    if not name:
        return JsonResponse({"error": "Room name is required"}, status=400)
    if kind not in ChannelKind.values:
        return JsonResponse({"error": "Invalid room kind"}, status=400)

    room, created = Room.objects.get_or_create(
        name=name,
        defaults={"created_by": request.user, "kind": kind},
    )
    if not created and room.created_by_id is None:
        room.created_by = request.user
        room.kind = kind
        room.save(update_fields=["created_by", "kind"])

    return JsonResponse(
        {
            "room": {
                "id": room.id,
                "name": room.name,
                "kind": room.kind,
                "created_at": room.created_at,
                "created_by_id": room.created_by_id,
            },
            "created": created,
        }
    )


@require_http_methods(["GET", "DELETE"])
def api_room_detail(request, room_id):
    room = get_object_or_404(
        Room.objects.only("id", "name", "kind", "created_at", "created_by"), pk=room_id
    )
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    if request.method == "GET":
        return JsonResponse(
            {
                "room": {
                    "id": room.id,
                    "name": room.name,
                    "kind": room.kind,
                    "created_at": room.created_at,
                    "created_by_id": room.created_by_id,
                }
            }
        )

    if not (request.user.is_superuser or room.created_by_id == request.user.id):
        return JsonResponse(
            {"error": "Only room owner can delete this room"}, status=403
        )

    room.delete()
    return JsonResponse({"deleted": True})


@require_http_methods(["GET"])
def api_room_messages(request, room_name):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    limit, offset = _parse_pagination(request.GET)
    if limit is None:
        return JsonResponse({"error": "Invalid limit/offset"}, status=400)

    room = Room.objects.filter(name=room_name).only("id", "kind").first()
    if room is None:
        return JsonResponse({"error": "Room not found"}, status=404)
    if room.kind not in (ChannelKind.CHAT, ChannelKind.VOICE):
        return JsonResponse(
            {"error": "History only available for chat channels"}, status=400
        )

    rows = list(
        room.messages.select_related("room", "sticker")
        .only(
            "id",
            "alias",
            "content",
            "timestamp",
            "room__name",
            "sticker",
            "sticker__name",
            "sticker__image",
            "attachment",
            "attachment_name",
            "attachment_mime",
        )
        .order_by("-timestamp")[offset : offset + limit + 1]
    )

    has_more = len(rows) > limit
    rows = rows[:limit]
    rows.reverse()

    messages_payload = [
        serialize_message(msg, source="history")
        for msg in rows
    ]

    return JsonResponse(
        {
            "room": room_name,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "messages": messages_payload,
        }
    )


@login_required
@require_http_methods(["POST"])
def api_room_attachment(request, room_name):
    room = Room.objects.filter(name=room_name).only("id", "kind").first()
    if room is None:
        return JsonResponse({"error": "Room not found"}, status=404)
    if room.kind not in (ChannelKind.CHAT, ChannelKind.VOICE):
        return JsonResponse(
            {"error": "Attachments only available for chat channels"}, status=400
        )

    alias = _ensure_profile(request.user).nickname
    message_text = (request.POST.get("message") or "").strip()[:1000]
    attachment = request.FILES.get("attachment")
    sticker_id = _parse_int(request.POST.get("sticker_id"))
    sticker = None

    if sticker_id:
        sticker = (
            Sticker.objects.filter(id=sticker_id, owner=request.user)
            .only("id", "name", "image")
            .first()
        )
        if sticker is None:
            return JsonResponse({"error": "Sticker no encontrado"}, status=404)

    if not attachment and not message_text and sticker is None:
        return JsonResponse(
            {"error": "Attachment, sticker or message is required"}, status=400
        )

    payload = create_message_payload(
        room_name,
        alias,
        content=message_text,
        attachment=attachment,
        attachment_name=getattr(attachment, "name", "") or "",
        attachment_mime=getattr(attachment, "content_type", "") or "",
        sticker=sticker,
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{room_name}", {"type": "chat_message", **payload}
    )

    return JsonResponse({"message": payload}, status=201)


@login_required
@require_http_methods(["GET", "POST"])
def api_stickers(request):
    if request.method == "GET":
        stickers = list(
            Sticker.objects.filter(owner=request.user)
            .only("id", "name", "image", "created_at")
            .values("id", "name", "image", "created_at")
        )
        for item in stickers:
            item["url"] = (
                settings.MEDIA_URL + item["image"] if item.get("image") else ""
            )
            item.pop("image", None)
        return JsonResponse({"stickers": stickers})

    sticker_file = request.FILES.get("sticker")
    name = (request.POST.get("name") or "").strip()[:60]
    if not sticker_file:
        return JsonResponse({"error": "Debes seleccionar una imagen"}, status=400)
    if not (sticker_file.content_type or "").startswith("image/"):
        return JsonResponse({"error": "El sticker debe ser una imagen"}, status=400)
    if not name:
        name = sticker_file.name.rsplit(".", 1)[0][:60] or "Sticker"

    sticker = Sticker.objects.create(owner=request.user, name=name, image=sticker_file)
    return JsonResponse(
        {
            "sticker": {
                "id": sticker.id,
                "name": sticker.name,
                "url": sticker.image.url,
                "created_at": sticker.created_at,
            }
        },
        status=201,
    )


@login_required
@require_http_methods(["DELETE"])
def api_sticker_detail(request, sticker_id):
    deleted, _ = Sticker.objects.filter(id=sticker_id, owner=request.user).delete()
    if not deleted:
        return JsonResponse({"error": "Sticker no encontrado"}, status=404)
    return JsonResponse({"deleted": True})
