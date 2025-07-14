import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# More efficient message tracking with chat-specific lists
sent_messages = defaultdict(list)

async def send_and_track_message(message_func, *args, **kwargs):
    """Send a message and track it for later deletion"""
    try:
        msg = await message_func(*args, **kwargs)
        sent_messages[msg.chat_id].append(msg.message_id)
        return msg
    except Exception as e:
        logger.error(f"Errore nell'invio del messaggio: {e}")
        return None

async def delete_old_messages(context):
    """Delete old messages and clean up tracking data"""
    global sent_messages
    deleted_count = 0
    
    for chat_id, message_ids in list(sent_messages.items()):
        for message_id in message_ids[:]:  # Create a copy to iterate safely
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Impossibile cancellare messaggio {message_id} in chat {chat_id}: {e}")
            finally:
                # Remove from tracking regardless of success
                message_ids.remove(message_id)
        
        # Clean up empty lists
        if not message_ids:
            del sent_messages[chat_id]
    
    if deleted_count > 0:
        logger.info(f"Cancellati {deleted_count} messaggi automaticamente")