import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { getUserNotifications, markNotificationAsRead } from '../api';

const NotificationContext = createContext(null);

export const NotificationProvider = ({ children }) => {
    const { isAuthenticated } = useAuth();
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(false);
    const fetchingRef = React.useRef(false);

    const fetchNotifications = useCallback(async () => {
        if (!isAuthenticated) return;

        if (fetchingRef.current) return;
        fetchingRef.current = true;
        setLoading(true);

        try {
            const data = await getUserNotifications();
            setNotifications(data);
        } catch (err) {
            console.error('Failed to fetch notifications:', err);
        } finally {
            fetchingRef.current = false;
            setLoading(false);
        }
    }, [isAuthenticated]);

    // Initial fetch and polling
    useEffect(() => {
        if (!isAuthenticated) return;

        fetchNotifications();

        let interval;

        const startInterval = () => {
            clearInterval(interval);
            interval = setInterval(() => {
                if (document.visibilityState === 'visible') {
                    fetchNotifications();
                }
            }, 30000); // Poll every 30s only when tab is visible
        };

        startInterval();

        const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
                fetchNotifications();
                startInterval(); // Reset interval timeline on visible transition
            }
        };

        document.addEventListener('visibilitychange', handleVisibilityChange);

        return () => {
            clearInterval(interval);
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, [fetchNotifications, isAuthenticated]);

    const markAsRead = async (notifId) => {
        // Optimistic UI update
        setNotifications(prev => prev.map(n =>
            n.id === notifId ? { ...n, is_read: true } : n
        ));

        try {
            await markNotificationAsRead(notifId);
        } catch (err) {
            console.error('Failed to mark notification as read:', err);
            await fetchNotifications();
        }
    };

    const refreshNotifications = () => {
        fetchNotifications();
    };

    const unreadCount = notifications.filter(n => !n.is_read).length;
    const actionRequiredNotification = notifications.find(n => n.notification_type === 'ACTION_REQUIRED' && !n.is_read);

    return (
        <NotificationContext.Provider value={{
            notifications,
            unreadCount,
            actionRequiredNotification,
            markAsRead,
            refreshNotifications,
            loading
        }}>
            {children}
        </NotificationContext.Provider>
    );
};

export const useNotifications = () => {
    const context = useContext(NotificationContext);
    if (!context) {
        throw new Error('useNotifications must be used within a NotificationProvider');
    }
    return context;
};
