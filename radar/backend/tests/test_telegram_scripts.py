from app.scripts.telegram_chat_id import _chat_from_update, _chat_label


def test_extract_private_chat_from_message_update() -> None:
    update = {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "chat": {
                "id": 123456789,
                "type": "private",
                "first_name": "Radar",
                "last_name": "Tester",
            },
        },
    }

    chat = _chat_from_update(update)

    assert chat is not None
    assert chat["id"] == 123456789
    assert _chat_label(chat) == "Radar Tester"


def test_extract_group_chat_from_membership_update() -> None:
    update = {
        "update_id": 2,
        "my_chat_member": {
            "chat": {"id": -1001234567890, "type": "supergroup", "title": "Radar Alerts"}
        },
    }

    chat = _chat_from_update(update)

    assert chat is not None
    assert chat["id"] == -1001234567890
    assert _chat_label(chat) == "Radar Alerts"
