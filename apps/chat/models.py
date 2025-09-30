# apps/chat/models.py

from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

class Conversation(models.Model):
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    participants = models.ManyToManyField(
        User,
        through='ConversationParticipant',
        related_name='conversations'
    )
    
    def __str__(self):
        return f"Conversation {self.id}"

class ConversationParticipant(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='conversation_participants' # Good practice to add a related_name
    )
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE,
        related_name='conversation_participants'
    )
    
    class Meta:
        unique_together = ('user', 'conversation')
        
    def __str__(self):
        return f"{self.user.username} in Conversation {self.conversation.id}"