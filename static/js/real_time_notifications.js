// Real-time notification system
class RealTimeNotifications {
    constructor() {
        this.socket = null;
        this.notificationCount = 0;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        
        this.init();
    }
    
    init() {
        if (typeof window.currentUserId !== 'undefined' && window.currentUserId) {
            this.connectWebSocket();
            this.setupUI();
            this.requestNotificationPermission();
        }
    }
    
    connectWebSocket() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = () => {
                console.log('Notification WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.reconnectDelay = 1000;
                this.updateConnectionStatus(true);
            };
            
            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            };
            
            this.socket.onclose = (event) => {
                console.log('Notification WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus(false);
                this.scheduleReconnect();
            };
            
            this.socket.onerror = (error) => {
                console.error('Notification WebSocket error:', error);
                this.isConnected = false;
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.scheduleReconnect();
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            
            console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, delay);
        } else {
            console.log('Max reconnection attempts reached');
        }
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'notification_count':
                this.updateNotificationCount(data.count);
                break;
            case 'new_notification':
                this.handleNewNotification(data.notification);
                break;
            case 'notification_read':
                this.handleNotificationRead(data.notification_id);
                break;
        }
    }
    
    handleNewNotification(notification) {
        this.notificationCount++;
        this.updateNotificationCount(this.notificationCount);
        this.showNotificationToast(notification);
        this.playNotificationSound();
        this.showBrowserNotification(notification);
        this.addToNotificationDropdown(notification);
    }
    
    handleNotificationRead(notificationId) {
        if (this.notificationCount > 0) {
            this.notificationCount--;
            this.updateNotificationCount(this.notificationCount);
        }
        this.removeFromNotificationDropdown(notificationId);
    }
    
    updateNotificationCount(count) {
        this.notificationCount = count;
        const badges = document.querySelectorAll('.notification-badge, .notification-count');
        
        badges.forEach(badge => {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
                badge.classList.add('animate-pulse');
            } else {
                badge.style.display = 'none';
                badge.classList.remove('animate-pulse');
            }
        });
        
        // Update page title
        if (count > 0) {
            document.title = `(${count}) ${document.title.replace(/^\(\d+\)\s/, '')}`;
        } else {
            document.title = document.title.replace(/^\(\d+\)\s/, '');
        }
    }
    
    showNotificationToast(notification) {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'notification-toast';
        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-icon">
                    <i class="${this.getNotificationIcon(notification.type)}"></i>
                </div>
                <div class="toast-body">
                    <div class="toast-title">${this.getNotificationTitle(notification.type)}</div>
                    <div class="toast-text">${notification.content}</div>
                </div>
                <button class="toast-close" onclick="this.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // Add to page
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
        
        // Add click handler
        toast.addEventListener('click', () => {
            this.handleNotificationClick(notification);
            toast.remove();
        });
    }
    
    addToNotificationDropdown(notification) {
        const dropdown = document.querySelector('.notification-dropdown-menu');
        if (!dropdown) return;
        
        const notificationElement = document.createElement('div');
        notificationElement.className = 'notification-item unread';
        notificationElement.dataset.notificationId = notification.id;
        notificationElement.innerHTML = `
            <div class="notification-icon ${notification.type}">
                <i class="${this.getNotificationIcon(notification.type)}"></i>
            </div>
            <div class="notification-content">
                <div class="notification-title">${this.getNotificationTitle(notification.type)}</div>
                <div class="notification-text">${notification.content}</div>
                <div class="notification-time">${this.getTimeAgo(new Date(notification.created_at))}</div>
            </div>
        `;
        
        // Add click handler
        notificationElement.addEventListener('click', () => {
            this.markAsRead(notification.id);
            this.handleNotificationClick(notification);
        });
        
        // Insert at the top
        dropdown.insertBefore(notificationElement, dropdown.firstChild);
        
        // Limit to 10 notifications in dropdown
        const items = dropdown.querySelectorAll('.notification-item');
        if (items.length > 10) {
            items[items.length - 1].remove();
        }
    }
    
    removeFromNotificationDropdown(notificationId) {
        const item = document.querySelector(`[data-notification-id="${notificationId}"]`);
        if (item) {
            item.classList.remove('unread');
            item.classList.add('read');
        }
    }
    
    markAsRead(notificationId) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'mark_read',
                notification_id: notificationId
            }));
        }
    }
    
    markAllAsRead() {
        const unreadItems = document.querySelectorAll('.notification-item.unread');
        unreadItems.forEach(item => {
            const notificationId = item.dataset.notificationId;
            this.markAsRead(parseInt(notificationId));
        });
    }
    
    handleNotificationClick(notification) {
        // Navigate to relevant page based on notification type
        switch (notification.type) {
            case 'new_job_posting':
                if (notification.related_id) {
                    window.location.href = `/jobs/${notification.related_id}/`;
                }
                break;
            case 'application_update':
                window.location.href = '/accounts/applications/';
                break;
            case 'interview_scheduled':
                window.location.href = '/accounts/interviews/';
                break;
            default:
                console.log('Notification clicked:', notification);
        }
    }
    
    getNotificationIcon(type) {
        const icons = {
            'new_job_posting': 'fas fa-briefcase',
            'application_update': 'fas fa-file-alt',
            'interview_scheduled': 'fas fa-calendar-check',
            'system': 'fas fa-cog',
            'message': 'fas fa-envelope'
        };
        return icons[type] || 'fas fa-bell';
    }
    
    getNotificationTitle(type) {
        const titles = {
            'new_job_posting': 'New Job Alert',
            'application_update': 'Application Update',
            'interview_scheduled': 'Interview Scheduled',
            'system': 'System Notification',
            'message': 'New Message'
        };
        return titles[type] || 'Notification';
    }
    
    getTimeAgo(date) {
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    }
    
    playNotificationSound() {
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(e => console.log('Could not play notification sound'));
        } catch (e) {
            console.log('Notification sound not available');
        }
    }
    
    showBrowserNotification(notification) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const browserNotification = new Notification(this.getNotificationTitle(notification.type), {
                body: notification.content,
                icon: '/static/favicon.ico',
                badge: '/static/favicon.ico',
                tag: `notification-${notification.id}`,
                requireInteraction: false
            });
            
            browserNotification.onclick = () => {
                window.focus();
                this.handleNotificationClick(notification);
                browserNotification.close();
            };
            
            // Auto-close after 5 seconds
            setTimeout(() => {
                browserNotification.close();
            }, 5000);
        }
    }
    
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                console.log('Notification permission:', permission);
            });
        }
    }
    
    setupUI() {
        // Add notification bell to navigation if it doesn't exist
        this.createNotificationBell();
        
        // Setup notification dropdown
        this.setupNotificationDropdown();
        
        // Add CSS for notifications
        this.addNotificationStyles();
    }
    
    createNotificationBell() {
        const nav = document.querySelector('.navbar-nav');
        if (!nav || document.querySelector('.notification-bell')) return;
        
        const bellHTML = `
            <li class="nav-item dropdown notification-bell">
                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="fas fa-bell"></i>
                    <span class="notification-badge" style="display: none;">0</span>
                </a>
                <div class="dropdown-menu dropdown-menu-end notification-dropdown">
                    <div class="dropdown-header d-flex justify-content-between align-items-center">
                        <span>Notifications</span>
                        <button class="btn btn-sm btn-link p-0" onclick="notificationSystem.markAllAsRead()">
                            Mark all read
                        </button>
                    </div>
                    <div class="notification-dropdown-menu">
                        <div class="text-center py-3 text-muted">
                            <i class="fas fa-bell-slash fa-2x mb-2"></i>
                            <p>No notifications yet</p>
                        </div>
                    </div>
                    <div class="dropdown-footer">
                        <a href="/accounts/notifications/" class="btn btn-sm btn-primary w-100">
                            View All Notifications
                        </a>
                    </div>
                </div>
            </li>
        `;
        
        nav.insertAdjacentHTML('beforeend', bellHTML);
    }
    
    setupNotificationDropdown() {
        // Load recent notifications via AJAX
        this.loadRecentNotifications();
    }
    
    loadRecentNotifications() {
        // This would typically load from an API endpoint
        // For now, we'll rely on WebSocket messages
    }
    
    addNotificationStyles() {
        if (document.querySelector('#notification-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            .notification-badge {
                position: absolute;
                top: -5px;
                right: -5px;
                background: #dc3545;
                color: white;
                border-radius: 50%;
                padding: 2px 6px;
                font-size: 0.7rem;
                font-weight: bold;
                min-width: 18px;
                text-align: center;
            }
            
            .notification-dropdown {
                width: 350px;
                max-height: 400px;
                overflow-y: auto;
            }
            
            .notification-item {
                display: flex;
                padding: 12px 16px;
                border-bottom: 1px solid #eee;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            
            .notification-item:hover {
                background-color: #f8f9fa;
            }
            
            .notification-item.unread {
                background-color: #e3f2fd;
                border-left: 3px solid #2196f3;
            }
            
            .notification-icon {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 12px;
                color: white;
                font-size: 16px;
            }
            
            .notification-icon.new_job_posting { background: #28a745; }
            .notification-icon.application_update { background: #ffc107; }
            .notification-icon.interview_scheduled { background: #17a2b8; }
            .notification-icon.system { background: #6f42c1; }
            .notification-icon.message { background: #007bff; }
            
            .notification-content {
                flex: 1;
            }
            
            .notification-title {
                font-weight: 600;
                font-size: 0.9rem;
                margin-bottom: 4px;
            }
            
            .notification-text {
                font-size: 0.8rem;
                color: #666;
                line-height: 1.3;
                margin-bottom: 4px;
            }
            
            .notification-time {
                font-size: 0.7rem;
                color: #999;
            }
            
            .toast-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
            }
            
            .notification-toast {
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                margin-bottom: 10px;
                min-width: 300px;
                max-width: 400px;
                animation: slideInRight 0.3s ease-out;
                cursor: pointer;
            }
            
            .toast-content {
                display: flex;
                align-items: flex-start;
                padding: 16px;
            }
            
            .toast-icon {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: #007bff;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 12px;
                flex-shrink: 0;
            }
            
            .toast-body {
                flex: 1;
            }
            
            .toast-title {
                font-weight: 600;
                margin-bottom: 4px;
            }
            
            .toast-text {
                font-size: 0.9rem;
                color: #666;
                line-height: 1.3;
            }
            
            .toast-close {
                background: none;
                border: none;
                color: #999;
                cursor: pointer;
                padding: 4px;
                margin-left: 8px;
            }
            
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            .animate-pulse {
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }
        `;
        
        document.head.appendChild(styles);
    }
    
    updateConnectionStatus(connected) {
        const indicators = document.querySelectorAll('.connection-status, .status-indicator');
        indicators.forEach(indicator => {
            if (connected) {
                indicator.classList.remove('text-danger');
                indicator.classList.add('text-success');
                indicator.textContent = 'Connected';
            } else {
                indicator.classList.remove('text-success');
                indicator.classList.add('text-danger');
                indicator.textContent = 'Disconnected';
            }
        });
    }
}

// Initialize notification system when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.notificationSystem = new RealTimeNotifications();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RealTimeNotifications;
}
