"""
Telegram Log Bot - Admin Log'daki HER ŞEYİ log grubuna atar
"""

import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import (
    ChannelAdminLogEventActionChangeTitle,
    ChannelAdminLogEventActionChangeAbout,
    ChannelAdminLogEventActionChangeUsername,
    ChannelAdminLogEventActionChangePhoto,
    ChannelAdminLogEventActionToggleInvites,
    ChannelAdminLogEventActionToggleSignatures,
    ChannelAdminLogEventActionUpdatePinned,
    ChannelAdminLogEventActionEditMessage,
    ChannelAdminLogEventActionDeleteMessage,
    ChannelAdminLogEventActionParticipantJoin,
    ChannelAdminLogEventActionParticipantLeave,
    ChannelAdminLogEventActionParticipantInvite,
    ChannelAdminLogEventActionParticipantToggleBan,
    ChannelAdminLogEventActionParticipantToggleAdmin,
    ChannelAdminLogEventActionChangeStickerSet,
    ChannelAdminLogEventActionTogglePreHistoryHidden,
    ChannelAdminLogEventActionDefaultBannedRights,
    ChannelAdminLogEventActionStopPoll,
    ChannelAdminLogEventActionChangeLinkedChat,
    ChannelAdminLogEventActionChangeLocation,
    ChannelAdminLogEventActionToggleSlowMode,
    ChannelAdminLogEventActionStartGroupCall,
    ChannelAdminLogEventActionDiscardGroupCall,
    ChannelAdminLogEventActionParticipantMute,
    ChannelAdminLogEventActionParticipantUnmute,
    ChannelAdminLogEventActionToggleGroupCallSetting,
    ChannelAdminLogEventActionParticipantJoinByInvite,
    ChannelAdminLogEventActionExportedInviteDelete,
    ChannelAdminLogEventActionExportedInviteRevoke,
    ChannelAdminLogEventActionExportedInviteEdit,
    ChannelAdminLogEventActionParticipantVolume,
    ChannelAdminLogEventActionChangeHistoryTTL,
    ChannelAdminLogEventActionParticipantJoinByRequest,
    ChannelAdminLogEventActionToggleNoForwards,
    ChannelAdminLogEventActionSendMessage,
    ChannelAdminLogEventActionChangeAvailableReactions,
    ChannelAdminLogEventActionChangeUsernames,
    ChannelAdminLogEventActionToggleForum,
    ChannelAdminLogEventActionCreateTopic,
    ChannelAdminLogEventActionEditTopic,
    ChannelAdminLogEventActionDeleteTopic,
    ChannelAdminLogEventActionPinTopic,
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageMediaWebPage,
    MessageMediaGeo,
    MessageMediaContact,
    MessageMediaPoll,
    MessageMediaDice,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    DocumentAttributeAudio,
    DocumentAttributeSticker,
    DocumentAttributeAnimated,
    ChatBannedRights,
    ChatAdminRights,
    PeerChannel,
    User,
)
from telethon.tl.functions.channels import GetAdminLogRequest
from telethon.tl.types import ChannelAdminLogEventsFilter
import config

# Client (StringSession ile Heroku uyumlu)
client = TelegramClient(StringSession(config.STRING_SESSION), config.API_ID, config.API_HASH)

# Son işlenen event ID
last_event_id = 0

# Mesaj cache (silinen mesajları göstermek için)
message_cache = {}

def get_user_info(user) -> str:
    """Kullanıcı bilgisini formatla"""
    if not user:
        return "Bilinmiyor"

    name = ""
    if hasattr(user, 'first_name') and user.first_name:
        name = user.first_name
    if hasattr(user, 'last_name') and user.last_name:
        name += f" {user.last_name}"

    if not name:
        name = "İsimsiz"

    user_id = user.id if hasattr(user, 'id') else 0
    username = f"@{user.username}" if hasattr(user, 'username') and user.username else ""

    mention = f"[{name}](tg://user?id={user_id})"

    return f"{mention} {username}\n`ID: {user_id}`"


def format_date(dt) -> str:
    """Tarihi formatla"""
    if not dt:
        return "Bilinmiyor"
    return dt.strftime("%d.%m.%Y %H:%M:%S")


def get_media_info(media) -> str:
    """Medya bilgisini al"""
    if not media:
        return None

    if isinstance(media, MessageMediaPhoto):
        return "🖼️ **Fotoğraf**"

    elif isinstance(media, MessageMediaDocument):
        doc = media.document
        if doc:
            # Dosya türünü belirle
            for attr in doc.attributes:
                if isinstance(attr, DocumentAttributeSticker):
                    return f"🎭 **Sticker**"
                elif isinstance(attr, DocumentAttributeAnimated):
                    return f"🎞️ **GIF**"
                elif isinstance(attr, DocumentAttributeVideo):
                    if attr.round_message:
                        return f"⭕ **Video Mesaj** ({attr.duration}sn)"
                    return f"🎬 **Video** ({attr.duration}sn, {attr.w}x{attr.h})"
                elif isinstance(attr, DocumentAttributeAudio):
                    if attr.voice:
                        return f"🎤 **Sesli Mesaj** ({attr.duration}sn)"
                    return f"🎵 **Ses** ({attr.duration}sn)"
                elif isinstance(attr, DocumentAttributeFilename):
                    size = doc.size / 1024 / 1024
                    return f"📎 **Dosya:** {attr.file_name} ({size:.2f}MB)"

            return f"📎 **Belge**"

    elif isinstance(media, MessageMediaWebPage):
        return f"🔗 **Web Önizleme**"

    elif isinstance(media, MessageMediaGeo):
        return f"📍 **Konum**"

    elif isinstance(media, MessageMediaContact):
        return f"👤 **Kişi**"

    elif isinstance(media, MessageMediaPoll):
        return f"📊 **Anket**"

    elif isinstance(media, MessageMediaDice):
        return f"🎲 **Zar:** {media.value}"

    return "📦 **Medya**"


def format_banned_rights(rights: ChatBannedRights) -> str:
    """Yasak haklarını formatla"""
    if not rights:
        return "Yok"

    bans = []
    if rights.view_messages: bans.append("Mesaj Görme")
    if rights.send_messages: bans.append("Mesaj Gönderme")
    if rights.send_media: bans.append("Medya Gönderme")
    if rights.send_stickers: bans.append("Sticker")
    if rights.send_gifs: bans.append("GIF")
    if rights.send_games: bans.append("Oyun")
    if rights.send_inline: bans.append("Inline Bot")
    if rights.embed_links: bans.append("Link Önizleme")
    if rights.send_polls: bans.append("Anket")
    if rights.change_info: bans.append("Bilgi Değiştirme")
    if rights.invite_users: bans.append("Davet Etme")
    if rights.pin_messages: bans.append("Sabitleme")

    if not bans:
        return "Kısıtlama Yok"

    return ", ".join(bans)


def format_admin_rights(rights: ChatAdminRights) -> str:
    """Admin haklarını formatla"""
    if not rights:
        return "Yok"

    perms = []
    if rights.change_info: perms.append("Bilgi Değiştir")
    if rights.post_messages: perms.append("Mesaj Gönder")
    if rights.edit_messages: perms.append("Mesaj Düzenle")
    if rights.delete_messages: perms.append("Mesaj Sil")
    if rights.ban_users: perms.append("Yasakla")
    if rights.invite_users: perms.append("Davet Et")
    if rights.pin_messages: perms.append("Sabitle")
    if rights.add_admins: perms.append("Admin Ekle")
    if rights.anonymous: perms.append("Anonim")
    if rights.manage_call: perms.append("Görüşme Yönet")
    if rights.other: perms.append("Diğer")

    if not perms:
        return "Yetki Yok"

    return ", ".join(perms)


async def send_log(text: str, file=None):
    """Log grubuna mesaj gönder"""
    try:
        await client.send_message(
            config.LOG_GROUP_ID,
            text,
            file=file,
            link_preview=False,
            parse_mode='md'
        )
    except Exception as e:
        print(f"Log gönderme hatası: {e}")


async def process_admin_log_event(event, users_dict):
    """Admin log eventini işle ve logla"""

    user = users_dict.get(event.user_id)
    user_info = get_user_info(user)
    date = format_date(event.date)
    action = event.action

    separator = "━" * 35

    # ==================== MESAJ SİLME ====================
    if isinstance(action, ChannelAdminLogEventActionDeleteMessage):
        msg = action.message
        text = msg.message if msg.message else ""
        media_info = get_media_info(msg.media) if msg.media else ""

        log_text = f"""🗑️ **MESAJ SİLİNDİ**
{separator}

👤 **Silen:** {user_info}

📝 **Silinen Mesaj:**
{text if text else "(Metin yok)"}

{media_info if media_info else ""}

📅 **Tarih:** `{date}`
🆔 **Mesaj ID:** `{msg.id}`"""

        # Medya varsa indir ve gönder
        if msg.media:
            try:
                file = await client.download_media(msg.media, bytes)
                await send_log(log_text, file=file)
            except:
                await send_log(log_text)
        else:
            await send_log(log_text)

    # ==================== MESAJ DÜZENLEME ====================
    elif isinstance(action, ChannelAdminLogEventActionEditMessage):
        old_msg = action.prev_message
        new_msg = action.new_message

        old_text = old_msg.message if old_msg.message else "(Metin yok)"
        new_text = new_msg.message if new_msg.message else "(Metin yok)"

        log_text = f"""✏️ **MESAJ DÜZENLENDİ**
{separator}

👤 **Düzenleyen:** {user_info}

📝 **Eski Mesaj:**
{old_text}

📝 **Yeni Mesaj:**
{new_text}

📅 **Tarih:** `{date}`
🆔 **Mesaj ID:** `{new_msg.id}`"""

        await send_log(log_text)

    # ==================== MESAJ SABİTLEME ====================
    elif isinstance(action, ChannelAdminLogEventActionUpdatePinned):
        msg = action.message
        text = msg.message if msg and msg.message else ""
        pinned = "SABİTLENDİ" if msg and msg.id else "SABİT KALDIRILDI"
        emoji = "📌" if msg and msg.id else "📍"

        log_text = f"""{emoji} **MESAJ {pinned}**
{separator}

👤 **İşlemi Yapan:** {user_info}

📝 **Mesaj:**
{text if text else "(Metin yok)"}

📅 **Tarih:** `{date}`"""

        if msg and msg.media:
            media_info = get_media_info(msg.media)
            log_text += f"\n{media_info}"

        await send_log(log_text)

    # ==================== ÜYE KATILDI ====================
    elif isinstance(action, ChannelAdminLogEventActionParticipantJoin):
        log_text = f"""📥 **ÜYE KATILDI**
{separator}

👤 **Katılan:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== ÜYE AYRILDI ====================
    elif isinstance(action, ChannelAdminLogEventActionParticipantLeave):
        log_text = f"""📤 **ÜYE AYRILDI**
{separator}

👤 **Ayrılan:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== ÜYE DAVET EDİLDİ ====================
    elif isinstance(action, ChannelAdminLogEventActionParticipantInvite):
        invited_user = users_dict.get(action.participant.user_id)
        invited_info = get_user_info(invited_user)

        log_text = f"""📨 **ÜYE DAVET EDİLDİ**
{separator}

👤 **Davet Eden:** {user_info}
👤 **Davet Edilen:** {invited_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== LİNK İLE KATILDI ====================
    elif isinstance(action, ChannelAdminLogEventActionParticipantJoinByInvite):
        invite = action.invite
        link = invite.link if hasattr(invite, 'link') else "Bilinmiyor"

        log_text = f"""🔗 **LİNK İLE KATILDI**
{separator}

👤 **Katılan:** {user_info}
🔗 **Link:** `{link}`

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== İSTEK İLE KATILDI ====================
    elif isinstance(action, ChannelAdminLogEventActionParticipantJoinByRequest):
        log_text = f"""✋ **İSTEK İLE KATILDI**
{separator}

👤 **Katılan:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== BAN / UNBAN / KISITLAMA ====================
    elif isinstance(action, ChannelAdminLogEventActionParticipantToggleBan):
        target_user = users_dict.get(action.prev_participant.user_id) if hasattr(action.prev_participant, 'user_id') else None
        target_info = get_user_info(target_user) if target_user else "Bilinmiyor"

        new_rights = action.new_participant.banned_rights if hasattr(action.new_participant, 'banned_rights') else None
        old_rights = action.prev_participant.banned_rights if hasattr(action.prev_participant, 'banned_rights') else None

        # Ban mı, unban mı, kısıtlama mı?
        if new_rights and new_rights.view_messages:
            emoji = "🚫"
            action_text = "YASAKLANDI (BAN)"
        elif old_rights and old_rights.view_messages and (not new_rights or not new_rights.view_messages):
            emoji = "✅"
            action_text = "YASAK KALDIRILDI (UNBAN)"
        elif new_rights:
            emoji = "🔒"
            action_text = "KISITLANDI"
        else:
            emoji = "🔓"
            action_text = "KISITLAMA KALDIRILDI"

        new_restrictions = format_banned_rights(new_rights) if new_rights else "Yok"

        # Süre
        until = ""
        if new_rights and new_rights.until_date:
            until = f"\n⏰ **Süre:** `{format_date(new_rights.until_date)}`'e kadar"

        log_text = f"""{emoji} **{action_text}**
{separator}

👤 **İşlemi Yapan:** {user_info}
👤 **Hedef:** {target_info}

🔒 **Kısıtlamalar:** {new_restrictions}{until}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== ADMİN DEĞİŞİKLİĞİ ====================
    elif isinstance(action, ChannelAdminLogEventActionParticipantToggleAdmin):
        target_id = action.new_participant.user_id if hasattr(action.new_participant, 'user_id') else None
        target_user = users_dict.get(target_id) if target_id else None
        target_info = get_user_info(target_user) if target_user else "Bilinmiyor"

        new_rights = action.new_participant.admin_rights if hasattr(action.new_participant, 'admin_rights') else None
        old_rights = action.prev_participant.admin_rights if hasattr(action.prev_participant, 'admin_rights') else None

        if new_rights and not old_rights:
            emoji = "👑"
            action_text = "ADMİN YAPILDI"
        elif old_rights and not new_rights:
            emoji = "👤"
            action_text = "ADMİNLİK ALINDI"
        else:
            emoji = "⚙️"
            action_text = "ADMİN YETKİLERİ DEĞİŞTİ"

        new_perms = format_admin_rights(new_rights) if new_rights else "Yok"
        old_perms = format_admin_rights(old_rights) if old_rights else "Yok"

        rank = ""
        if hasattr(action.new_participant, 'rank') and action.new_participant.rank:
            rank = f"\n🏷️ **Ünvan:** `{action.new_participant.rank}`"

        log_text = f"""{emoji} **{action_text}**
{separator}

👤 **İşlemi Yapan:** {user_info}
👤 **Hedef:** {target_info}

📋 **Eski Yetkiler:** {old_perms}
📋 **Yeni Yetkiler:** {new_perms}{rank}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== GRUP ADI DEĞİŞTİ ====================
    elif isinstance(action, ChannelAdminLogEventActionChangeTitle):
        log_text = f"""📝 **GRUP ADI DEĞİŞTİ**
{separator}

👤 **Değiştiren:** {user_info}

📌 **Eski Ad:** `{action.prev_value}`
📌 **Yeni Ad:** `{action.new_value}`

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== GRUP AÇIKLAMASI DEĞİŞTİ ====================
    elif isinstance(action, ChannelAdminLogEventActionChangeAbout):
        log_text = f"""📄 **GRUP AÇIKLAMASI DEĞİŞTİ**
{separator}

👤 **Değiştiren:** {user_info}

📝 **Eski Açıklama:**
{action.prev_value if action.prev_value else "(Boş)"}

📝 **Yeni Açıklama:**
{action.new_value if action.new_value else "(Boş)"}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== KULLANICI ADI DEĞİŞTİ ====================
    elif isinstance(action, ChannelAdminLogEventActionChangeUsername):
        log_text = f"""🔗 **KULLANICI ADI DEĞİŞTİ**
{separator}

👤 **Değiştiren:** {user_info}

📌 **Eski:** @{action.prev_value if action.prev_value else "(Yok)"}
📌 **Yeni:** @{action.new_value if action.new_value else "(Yok)"}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== GRUP FOTOĞRAFI DEĞİŞTİ ====================
    elif isinstance(action, ChannelAdminLogEventActionChangePhoto):
        log_text = f"""🖼️ **GRUP FOTOĞRAFI DEĞİŞTİ**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        # Yeni fotoğrafı gönder
        if action.new_photo:
            try:
                file = await client.download_media(action.new_photo, bytes)
                await send_log(log_text, file=file)
            except:
                await send_log(log_text)
        else:
            await send_log(log_text + "\n\n(Fotoğraf kaldırıldı)")

    # ==================== DAVET LİNKİ AYARI ====================
    elif isinstance(action, ChannelAdminLogEventActionToggleInvites):
        status = "AKTİF" if action.new_value else "KAPALI"
        emoji = "🔓" if action.new_value else "🔒"

        log_text = f"""{emoji} **DAVET LİNKİ: {status}**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== İMZALAR AYARI ====================
    elif isinstance(action, ChannelAdminLogEventActionToggleSignatures):
        status = "AKTİF" if action.new_value else "KAPALI"

        log_text = f"""✍️ **İMZALAR: {status}**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== YAVAS MOD ====================
    elif isinstance(action, ChannelAdminLogEventActionToggleSlowMode):
        if action.new_value == 0:
            status = "KAPALI"
        else:
            status = f"{action.new_value} saniye"

        log_text = f"""🐢 **YAVAŞ MOD: {status}**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== GEÇMİŞ GİZLİLİĞİ ====================
    elif isinstance(action, ChannelAdminLogEventActionTogglePreHistoryHidden):
        status = "GİZLİ" if action.new_value else "GÖRÜNÜR"

        log_text = f"""📜 **MESAJ GEÇMİŞİ: {status}**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== VARSAYILAN KISITLAMALAR ====================
    elif isinstance(action, ChannelAdminLogEventActionDefaultBannedRights):
        new_rights = format_banned_rights(action.new_banned_rights)
        old_rights = format_banned_rights(action.prev_banned_rights)

        log_text = f"""🔒 **VARSAYILAN KISITLAMALAR DEĞİŞTİ**
{separator}

👤 **Değiştiren:** {user_info}

📋 **Eski:** {old_rights}
📋 **Yeni:** {new_rights}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== STİCKER SETİ ====================
    elif isinstance(action, ChannelAdminLogEventActionChangeStickerSet):
        log_text = f"""🎭 **STİCKER SETİ DEĞİŞTİ**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== ANKET DURDURULDU ====================
    elif isinstance(action, ChannelAdminLogEventActionStopPoll):
        msg = action.message

        log_text = f"""📊 **ANKET DURDURULDU**
{separator}

👤 **Durduran:** {user_info}

📅 **Tarih:** `{date}`
🆔 **Mesaj ID:** `{msg.id}`"""

        await send_log(log_text)

    # ==================== BAĞLI SOHBET DEĞİŞTİ ====================
    elif isinstance(action, ChannelAdminLogEventActionChangeLinkedChat):
        log_text = f"""🔗 **BAĞLI SOHBET DEĞİŞTİ**
{separator}

👤 **Değiştiren:** {user_info}

📌 **Eski ID:** `{action.prev_value}`
📌 **Yeni ID:** `{action.new_value}`

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== KONUM DEĞİŞTİ ====================
    elif isinstance(action, ChannelAdminLogEventActionChangeLocation):
        log_text = f"""📍 **KONUM DEĞİŞTİ**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== GÖRÜNTÜLÜ GÖRÜŞME BAŞLADI ====================
    elif isinstance(action, ChannelAdminLogEventActionStartGroupCall):
        log_text = f"""📞 **GÖRÜŞME BAŞLADI**
{separator}

👤 **Başlatan:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== GÖRÜNTÜLÜ GÖRÜŞME BİTTİ ====================
    elif isinstance(action, ChannelAdminLogEventActionDiscardGroupCall):
        log_text = f"""📴 **GÖRÜŞME BİTTİ**
{separator}

👤 **Bitiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== GÖRÜŞMEDE SESİ KAPATILDI ====================
    elif isinstance(action, ChannelAdminLogEventActionParticipantMute):
        target = action.participant
        target_id = target.user_id if hasattr(target, 'user_id') else None
        target_user = users_dict.get(target_id) if target_id else None
        target_info = get_user_info(target_user) if target_user else "Bilinmiyor"

        log_text = f"""🔇 **SESİ KAPATILDI**
{separator}

👤 **İşlemi Yapan:** {user_info}
👤 **Hedef:** {target_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== GÖRÜŞMEDE SESİ AÇILDI ====================
    elif isinstance(action, ChannelAdminLogEventActionParticipantUnmute):
        target = action.participant
        target_id = target.user_id if hasattr(target, 'user_id') else None
        target_user = users_dict.get(target_id) if target_id else None
        target_info = get_user_info(target_user) if target_user else "Bilinmiyor"

        log_text = f"""🔊 **SESİ AÇILDI**
{separator}

👤 **İşlemi Yapan:** {user_info}
👤 **Hedef:** {target_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== GÖRÜŞME AYARLARI DEĞİŞTİ ====================
    elif isinstance(action, ChannelAdminLogEventActionToggleGroupCallSetting):
        status = "AKTİF" if action.join_muted else "KAPALI"

        log_text = f"""⚙️ **GÖRÜŞME: KATILIMDA SESİ KAPAT: {status}**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== DAVET LİNKİ SİLİNDİ ====================
    elif isinstance(action, ChannelAdminLogEventActionExportedInviteDelete):
        invite = action.invite
        link = invite.link if hasattr(invite, 'link') else "Bilinmiyor"

        log_text = f"""🗑️ **DAVET LİNKİ SİLİNDİ**
{separator}

👤 **Silen:** {user_info}
🔗 **Link:** `{link}`

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== DAVET LİNKİ İPTAL EDİLDİ ====================
    elif isinstance(action, ChannelAdminLogEventActionExportedInviteRevoke):
        invite = action.invite
        link = invite.link if hasattr(invite, 'link') else "Bilinmiyor"

        log_text = f"""🚫 **DAVET LİNKİ İPTAL EDİLDİ**
{separator}

👤 **İptal Eden:** {user_info}
🔗 **Link:** `{link}`

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== DAVET LİNKİ DÜZENLENDİ ====================
    elif isinstance(action, ChannelAdminLogEventActionExportedInviteEdit):
        log_text = f"""✏️ **DAVET LİNKİ DÜZENLENDİ**
{separator}

👤 **Düzenleyen:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== GÖRÜŞMEDE SES SEVİYESİ DEĞİŞTİ ====================
    elif isinstance(action, ChannelAdminLogEventActionParticipantVolume):
        target = action.participant
        volume = target.volume if hasattr(target, 'volume') else 100

        log_text = f"""🔉 **SES SEVİYESİ DEĞİŞTİ: %{volume // 100}**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== OTOMATİK SİLME SÜRESİ ====================
    elif isinstance(action, ChannelAdminLogEventActionChangeHistoryTTL):
        old_ttl = action.prev_value
        new_ttl = action.new_value

        def format_ttl(seconds):
            if seconds == 0:
                return "Kapalı"
            elif seconds < 60:
                return f"{seconds} saniye"
            elif seconds < 3600:
                return f"{seconds // 60} dakika"
            elif seconds < 86400:
                return f"{seconds // 3600} saat"
            else:
                return f"{seconds // 86400} gün"

        log_text = f"""⏱️ **OTOMATİK SİLME SÜRESİ DEĞİŞTİ**
{separator}

👤 **Değiştiren:** {user_info}

📌 **Eski:** {format_ttl(old_ttl)}
📌 **Yeni:** {format_ttl(new_ttl)}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== İLETME YASAĞI ====================
    elif isinstance(action, ChannelAdminLogEventActionToggleNoForwards):
        status = "AKTİF" if action.new_value else "KAPALI"
        emoji = "🚫" if action.new_value else "✅"

        log_text = f"""{emoji} **İLETME YASAĞI: {status}**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== KANALA MESAJ GÖNDERİLDİ ====================
    elif isinstance(action, ChannelAdminLogEventActionSendMessage):
        msg = action.message
        text = msg.message if msg.message else ""
        media_info = get_media_info(msg.media) if msg.media else ""

        log_text = f"""📤 **MESAJ GÖNDERİLDİ**
{separator}

👤 **Gönderen:** {user_info}

📝 **Mesaj:**
{text if text else "(Metin yok)"}

{media_info if media_info else ""}

📅 **Tarih:** `{date}`
🆔 **Mesaj ID:** `{msg.id}`"""

        if msg.media:
            try:
                file = await client.download_media(msg.media, bytes)
                await send_log(log_text, file=file)
            except:
                await send_log(log_text)
        else:
            await send_log(log_text)

    # ==================== TEPKİLER DEĞİŞTİ ====================
    elif isinstance(action, ChannelAdminLogEventActionChangeAvailableReactions):
        log_text = f"""😀 **TEPKİLER DEĞİŞTİ**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== KULLANICI ADLARI DEĞİŞTİ ====================
    elif isinstance(action, ChannelAdminLogEventActionChangeUsernames):
        old_usernames = ", ".join(action.prev_value) if action.prev_value else "Yok"
        new_usernames = ", ".join(action.new_value) if action.new_value else "Yok"

        log_text = f"""🔗 **KULLANICI ADLARI DEĞİŞTİ**
{separator}

👤 **Değiştiren:** {user_info}

📌 **Eski:** {old_usernames}
📌 **Yeni:** {new_usernames}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== FORUM MODU ====================
    elif isinstance(action, ChannelAdminLogEventActionToggleForum):
        status = "AKTİF" if action.new_value else "KAPALI"

        log_text = f"""💬 **FORUM MODU: {status}**
{separator}

👤 **Değiştiren:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== KONU OLUŞTURULDU ====================
    elif isinstance(action, ChannelAdminLogEventActionCreateTopic):
        topic = action.topic
        title = topic.title if hasattr(topic, 'title') else "Bilinmiyor"

        log_text = f"""📁 **KONU OLUŞTURULDU**
{separator}

👤 **Oluşturan:** {user_info}
📌 **Konu:** {title}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== KONU DÜZENLENDİ ====================
    elif isinstance(action, ChannelAdminLogEventActionEditTopic):
        new_topic = action.new_topic
        title = new_topic.title if hasattr(new_topic, 'title') else "Bilinmiyor"

        log_text = f"""✏️ **KONU DÜZENLENDİ**
{separator}

👤 **Düzenleyen:** {user_info}
📌 **Konu:** {title}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== KONU SİLİNDİ ====================
    elif isinstance(action, ChannelAdminLogEventActionDeleteTopic):
        topic = action.topic
        title = topic.title if hasattr(topic, 'title') else "Bilinmiyor"

        log_text = f"""🗑️ **KONU SİLİNDİ**
{separator}

👤 **Silen:** {user_info}
📌 **Konu:** {title}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== KONU SABİTLENDİ ====================
    elif isinstance(action, ChannelAdminLogEventActionPinTopic):
        log_text = f"""📌 **KONU SABİTLENDİ/SABİT KALDIRILDI**
{separator}

👤 **İşlemi Yapan:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)

    # ==================== BİLİNMEYEN EYLEM ====================
    else:
        action_name = type(action).__name__.replace("ChannelAdminLogEventAction", "")

        log_text = f"""❓ **BİLİNMEYEN EYLEM: {action_name}**
{separator}

👤 **Yapan:** {user_info}

📅 **Tarih:** `{date}`"""

        await send_log(log_text)


async def check_admin_log():
    """Admin log'u periyodik olarak kontrol et"""
    global last_event_id

    while True:
        try:
            result = await client(GetAdminLogRequest(
                channel=config.SOURCE_GROUP_ID,
                q='',
                min_id=last_event_id,
                max_id=0,
                limit=100,
                events_filter=None,
                admins=None
            ))

            users_dict = {u.id: u for u in result.users}
            events_list = sorted(result.events, key=lambda x: x.id)

            for event in events_list:
                if event.id > last_event_id:
                    await process_admin_log_event(event, users_dict)
                    last_event_id = event.id

        except Exception as e:
            print(f"Admin log hatası: {e}")

        await asyncio.sleep(5)


@client.on(events.NewMessage(chats=config.SOURCE_GROUP_ID))
async def cache_new_message(event):
    """Yeni mesajları cache'le"""
    msg = event.message
    message_cache[msg.id] = {
        'text': msg.message,
        'media': msg.media,
        'sender_id': msg.sender_id,
        'date': msg.date
    }
    if len(message_cache) > 10000:
        oldest_key = min(message_cache.keys())
        del message_cache[oldest_key]


@client.on(events.MessageEdited(chats=config.SOURCE_GROUP_ID))
async def on_message_edited(event):
    """Mesaj düzenlendiğinde gerçek zamanlı log"""
    msg = event.message
    old_data = message_cache.get(msg.id, {})
    old_text = old_data.get('text', '(Bilinmiyor)')

    message_cache[msg.id] = {
        'text': msg.message,
        'media': msg.media,
        'sender_id': msg.sender_id,
        'date': msg.date
    }

    if old_text != msg.message:
        try:
            sender = await client.get_entity(msg.sender_id)
            user_info = get_user_info(sender)
        except:
            user_info = f"`{msg.sender_id}`"

        separator = "━" * 35
        log_text = f"""✏️ **MESAJ DÜZENLENDİ (Gerçek Zamanlı)**
{separator}

👤 **Düzenleyen:** {user_info}

📝 **Eski Mesaj:**
{old_text}

📝 **Yeni Mesaj:**
{msg.message if msg.message else "(Metin yok)"}

📅 **Tarih:** `{format_date(msg.edit_date)}`
🆔 **Mesaj ID:** `{msg.id}`"""
        await send_log(log_text)


@client.on(events.MessageDeleted(chats=config.SOURCE_GROUP_ID))
async def on_message_deleted(event):
    """Mesaj silindiğinde gerçek zamanlı log"""
    for msg_id in event.deleted_ids:
        cached = message_cache.get(msg_id)
        if cached:
            separator = "━" * 35
            try:
                sender = await client.get_entity(cached['sender_id'])
                user_info = get_user_info(sender)
            except:
                user_info = f"`{cached.get('sender_id', 'Bilinmiyor')}`"

            text = cached.get('text', '')
            media_info = get_media_info(cached.get('media')) if cached.get('media') else ""

            log_text = f"""🗑️ **MESAJ SİLİNDİ (Gerçek Zamanlı)**
{separator}

👤 **Gönderen:** {user_info}

📝 **Silinen Mesaj:**
{text if text else "(Metin yok)"}

{media_info if media_info else ""}

📅 **Gönderilme:** `{format_date(cached.get('date'))}`
🆔 **Mesaj ID:** `{msg_id}`"""

            if cached.get('media'):
                try:
                    file = await client.download_media(cached['media'], bytes)
                    await send_log(log_text, file=file)
                except:
                    await send_log(log_text)
            else:
                await send_log(log_text)
            del message_cache[msg_id]


@client.on(events.ChatAction(chats=config.SOURCE_GROUP_ID))
async def on_chat_action(event):
    """Üye giriş/çıkış olayları"""
    separator = "━" * 35

    if event.user_joined or event.user_added:
        try:
            user = await event.get_user()
            user_info = get_user_info(user)
        except:
            user_info = "Bilinmiyor"

        if event.user_added:
            try:
                added_by = await event.get_added_by()
                added_by_info = get_user_info(added_by)
            except:
                added_by_info = "Bilinmiyor"
            log_text = f"""📨 **ÜYE EKLENDİ**
{separator}

👤 **Eklenen:** {user_info}
👤 **Ekleyen:** {added_by_info}

📅 **Tarih:** `{format_date(datetime.now())}`"""
        else:
            log_text = f"""📥 **ÜYE KATILDI**
{separator}

👤 **Katılan:** {user_info}

📅 **Tarih:** `{format_date(datetime.now())}`"""
        await send_log(log_text)

    elif event.user_left or event.user_kicked:
        try:
            user = await event.get_user()
            user_info = get_user_info(user)
        except:
            user_info = "Bilinmiyor"

        if event.user_kicked:
            log_text = f"""👢 **ÜYE ATILDI**
{separator}

👤 **Atılan:** {user_info}

📅 **Tarih:** `{format_date(datetime.now())}`"""
        else:
            log_text = f"""📤 **ÜYE AYRILDI**
{separator}

👤 **Ayrılan:** {user_info}

📅 **Tarih:** `{format_date(datetime.now())}`"""
        await send_log(log_text)


async def main():
    """Ana fonksiyon"""
    print("=" * 50)
    print("🤖 TELEGRAM LOG BOT")
    print("=" * 50)

    await client.start()
    print("✅ Telegram'a bağlandı!")

    me = await client.get_me()
    print(f"👤 Hesap: {me.first_name} (@{me.username})")

    try:
        source = await client.get_entity(config.SOURCE_GROUP_ID)
        log_group = await client.get_entity(config.LOG_GROUP_ID)
        print(f"📥 İzlenen Grup: {source.title}")
        print(f"📤 Log Grubu: {log_group.title}")
    except Exception as e:
        print(f"❌ Grup hatası: {e}")
        return

    print("=" * 50)
    print("🚀 Bot çalışıyor! Durdurmak için Ctrl+C")
    print("=" * 50)

    separator = "━" * 35
    await send_log(f"""🤖 **LOG BOT BAŞLATILDI**
{separator}

📥 **İzlenen:** {source.title}
👤 **Hesap:** {me.first_name}
📅 **Tarih:** `{format_date(datetime.now())}`

✅ Tüm eylemler loglanacak!""")

    asyncio.create_task(check_admin_log())
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n👋 Bot durduruldu!")
