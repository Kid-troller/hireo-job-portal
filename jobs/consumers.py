import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import JobPost
from accounts.models import JobSeekerProfile
import asyncio

class JobFeedConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'job_feed'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial job data
        jobs = await self.get_recent_jobs()
        await self.send(text_data=json.dumps({
            'type': 'job_feed_update',
            'jobs': jobs
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'request_update':
            jobs = await self.get_recent_jobs()
            await self.send(text_data=json.dumps({
                'type': 'job_feed_update',
                'jobs': jobs
            }))

    # Receive message from room group
    async def job_feed_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_recent_jobs(self):
        jobs = JobPost.objects.filter(status='active').select_related(
            'company', 'category', 'location'
        ).order_by('-created_at')[:20]
        
        job_list = []
        for job in jobs:
            job_list.append({
                'id': job.id,
                'title': job.title,
                'company': job.company.name,
                'location': f"{job.location.city}, {job.location.state}",
                'category': job.category.name,
                'employment_type': job.get_employment_type_display(),
                'salary': job.get_formatted_salary(),
                'created_at': job.created_at.isoformat(),
                'is_remote': job.is_remote,
                'is_featured': job.is_featured,
                'url': f'/jobs/{job.id}/'
            })
        
        return job_list

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user == AnonymousUser():
            await self.close()
            return
            
        self.room_group_name = f'notifications_{self.user.id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send unread notifications count
        unread_count = await self.get_unread_notifications_count()
        await self.send(text_data=json.dumps({
            'type': 'notification_count',
            'count': unread_count
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'mark_read':
            notification_id = text_data_json.get('notification_id')
            await self.mark_notification_read(notification_id)
        elif message_type == 'get_notifications':
            notifications = await self.get_user_notifications()
            await self.send(text_data=json.dumps({
                'type': 'notifications_list',
                'notifications': notifications
            }))

    # Receive message from room group
    async def notification_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_unread_notifications_count(self):
        from accounts.models import Notification
        return Notification.objects.filter(user=self.user, is_read=False).count()

    @database_sync_to_async
    def get_user_notifications(self):
        from accounts.models import Notification
        notifications = Notification.objects.filter(
            user=self.user
        ).order_by('-created_at')[:10]
        
        notification_list = []
        for notification in notifications:
            notification_list.append({
                'id': notification.id,
                'type': notification.notification_type,
                'content': notification.content,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat(),
                'related_id': notification.related_id
            })
        
        return notification_list

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        from accounts.models import Notification
        try:
            notification = Notification.objects.get(
                id=notification_id, user=self.user
            )
            notification.is_read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False
