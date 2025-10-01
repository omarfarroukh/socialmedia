# apps/chat/consumers.py
import json
import uuid
import datetime
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from cassandra.util import uuid_from_time
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, ConversationParticipant
from apps.chat.cassandra import cassandra_session
User = get_user_model()

def timeuuid_to_datetime(timeuuid_obj: uuid.UUID) -> datetime.datetime:
    uuid_timestamp = timeuuid_obj.time
    unix_timestamp = (uuid_timestamp / 1e7) - 12219292800
    return datetime.datetime.fromtimestamp(unix_timestamp, tz=datetime.timezone.utc)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        # TODO: Check if user is a participant of this conversation in Postgres
        
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # This is the main dispatcher for incoming WebSocket messages
    async def receive_json(self, content):
        command = content.get("type", None)

        if command == "new_message":
            await self.handle_new_message(content["message"])
        elif command == "typing":
            await self.handle_typing_indicator(content["status"])
        elif command == "read_receipt":
            await self.handle_read_receipt()

    # --- Handlers for specific commands ---

    async def handle_new_message(self, message_content):
        now = datetime.datetime.utcnow()
        time_uuid_for_db = uuid_from_time(now)

        message_data = {
            'conversation_id': uuid.UUID(self.conversation_id),
            'timestamp': time_uuid_for_db,
            'message_id': uuid.uuid4(),
            'author_id': self.user.id,
            'author_username': self.user.username,
            'content': message_content,
        }
        
        cassandra_session.execute(
            """
            INSERT INTO messages (conversation_id, timestamp, message_id, author_id, author_username, content)
            VALUES (%(conversation_id)s, %(timestamp)s, %(message_id)s, %(author_id)s, %(author_username)s, %(content)s)
            """,
            message_data
        )

        # Update last_message_at in Postgres
        await self.update_conversation_timestamp(now)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'conversation_id': self.conversation_id, # Keep this for routing on the client
                'message': {
                    # 👇 THE FIX: Change snake_case to camelCase to match GraphQL's output
                    'authorUsername': self.user.username, 
                    'content': message_content,
                    'timestamp': timeuuid_to_datetime(time_uuid_for_db).isoformat(),
                }
            }
        )
        
    async def handle_typing_indicator(self, status):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing.indicator',
                'username': self.user.username,
                'status': status # 'typing' or 'stopped'
            }
        )
        
    async def handle_read_receipt(self):
        now = datetime.datetime.utcnow()
        await self.update_participant_read_timestamp(now)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read.receipt',
                'username': self.user.username,
                'timestamp': now.isoformat(),
            }
        )

    # --- Methods to broadcast events back to the client ---

    async def chat_message(self, event):
        await self.send_json(event)

    async def typing_indicator(self, event):
        # Don't send typing indicators back to the user who is typing
        if event['username'] != self.user.username:
            await self.send_json(event)
            
    async def read_receipt(self, event):
        await self.send_json(event)

    # --- Database helpers ---
    @database_sync_to_async
    def update_conversation_timestamp(self, timestamp):
        Conversation.objects.filter(id=self.conversation_id).update(last_message_at=timestamp)

    @database_sync_to_async
    def update_participant_read_timestamp(self, timestamp):
        ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id,
            user=self.user
        ).update(last_read_timestamp=timestamp)