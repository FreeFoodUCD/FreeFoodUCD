'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Ensure we have the base URL without /api/v1
const BASE_URL = API_URL.replace(/\/api\/v1\/?$/, '');

interface DashboardStats {
  users: {
    total: number;
    whatsapp_verified: number;
    email_verified: number;
    active: number;
  };
  societies: {
    total: number;
    active: number;
    scraping_posts: number;
  };
  events: {
    total: number;
    upcoming: number;
  };
  posts: {
    total: number;
    free_food: number;
    processed: number;
  };
  scraping: {
    last_24h_attempts: number;
    success_rate: number;
    last_scrape: string | null;
  };
}

interface ScrapingLog {
  id: string;
  society_name: string;
  society_handle: string;
  scrape_type: string;
  status: string;
  items_found: number;
  error_message: string | null;
  duration_ms: number;
  created_at: string;
}

interface Post {
  id: string;
  society_name: string;
  society_handle: string;
  caption: string;
  source_url: string;
  detected_at: string;
  is_free_food: boolean;
  processed: boolean;
  event_created: boolean;
  feedback_submitted: boolean;
  event?: {
    id: string;
    title: string;
    start_time: string | null;
    location: string | null;
    confidence_score: number;
    notified: boolean;
    users_notified: number;
  };
  feedback?: {
    is_correct: boolean;
    notes: string | null;
    created_at: string;
  };
}

interface PostAnalytics {
  period_days: number;
  total_posts: number;
  total_reviewed: number;
  review_rate: number;
  accuracy: number;
  correct_count: number;
  incorrect_count: number;
  classification_errors: number;
  extraction_errors: number;
}

interface User {
  id: string;
  email: string;
  phone_number: string;
  whatsapp_verified: boolean;
  email_verified: boolean;
  is_active: boolean;
  created_at: string;
}

interface UpcomingEvent {
  id: string;
  title: string;
  description: string;
  location: string;
  start_time: string;
  end_time: string | null;
  society_name: string;
  society_handle: string;
  confidence_score: number;
  notified: boolean;
  notification_sent_at: string | null;
  reminder_sent: boolean;
  reminder_sent_at: string | null;
  hours_until: number;
  users_to_notify: number;
  is_active: boolean;
}

interface Society {
  id: string;
  name: string;
  instagram_handle: string;
  is_active: boolean;
  scrape_posts: boolean;
  scrape_stories: boolean;
  last_post_check: string | null;
  last_story_check: string | null;
  stats: {
    total_posts: number;
    total_events: number;
    recent_scrapes: number;
    success_rate: number;
  };
}

interface NotificationLog {
  id: string;
  event_title: string;
  society_name: string;
  user_email: string;
  user_phone: string;
  notification_type: string;
  status: string;
  sent_at: string;
  error_message: string | null;
}

interface NotificationStats {
  period_days: number;
  total_sent: number;
  by_channel: {
    whatsapp: number;
    email: number;
  };
  by_status: {
    successful: number;
    failed: number;
    pending: number;
  };
  delivery_rate: number;
  recent_failures: number;
}

interface SystemHealth {
  database: string;
  celery_worker: string;
  celery_beat: string;
  services: {
    apify: string;
    twilio: string;
    resend: string;
  };
}

interface ErrorLog {
  type: string;
  timestamp: string;
  source: string;
  error: string;
  details: string;
}

export default function AdminDashboard() {
  const router = useRouter();
  const [adminKey, setAdminKey] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [logs, setLogs] = useState<ScrapingLog[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [upcomingEvents, setUpcomingEvents] = useState<UpcomingEvent[]>([]);
  const [societies, setSocieties] = useState<Society[]>([]);
  const [notificationLogs, setNotificationLogs] = useState<NotificationLog[]>([]);
  const [notificationStats, setNotificationStats] = useState<NotificationStats | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [errorLogs, setErrorLogs] = useState<ErrorLog[]>([]);
  const [recentPosts, setRecentPosts] = useState<Post[]>([]);
  const [postAnalytics, setPostAnalytics] = useState<PostAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [newSociety, setNewSociety] = useState({
    name: '',
    instagram_handle: '',
    scrape_posts: true,
    scrape_stories: false
  });

  // Check if admin key is stored
  useEffect(() => {
    const storedKey = localStorage.getItem('admin_key');
    if (storedKey) {
      setAdminKey(storedKey);
      setIsAuthenticated(true);
      loadDashboardData(storedKey);
    }
  }, []);

  const handleLogin = async () => {
    try {
      // Test the admin key
      const response = await fetch(`${BASE_URL}/api/v1/admin/stats`, {
        headers: { 'X-Admin-Key': adminKey }
      });
      
      if (response.ok) {
        localStorage.setItem('admin_key', adminKey);
        setIsAuthenticated(true);
        loadDashboardData(adminKey);
        setMessage('');
      } else {
        setMessage('Invalid admin key');
      }
    } catch (error) {
      setMessage('Error connecting to server');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('admin_key');
    setIsAuthenticated(false);
    setAdminKey('');
  };

  const loadDashboardData = async (key: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/dashboard-stats`, {
        headers: { 'X-Admin-Key': key }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error loading dashboard:', error);
    }
    setLoading(false);
  };

  const loadScrapingLogs = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/scraping-logs?limit=50`, {
        headers: { 'X-Admin-Key': adminKey }
      });
      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs);
      }
    } catch (error) {
      console.error('Error loading logs:', error);
    }
    setLoading(false);
  };

  const loadPosts = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/posts?limit=50`, {
        headers: { 'X-Admin-Key': adminKey }
      });
      if (response.ok) {
        const data = await response.json();
        setPosts(data.posts);
      }
    } catch (error) {
      console.error('Error loading posts:', error);
    }
    setLoading(false);
  };

  const loadUsers = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/users`, {
        headers: { 'X-Admin-Key': adminKey }
      });
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users);
      }
    } catch (error) {
      console.error('Error loading users:', error);
    }
    setLoading(false);
  };

  const deleteUser = async (userId: string, userIdentifier: string) => {
    if (!confirm(`Are you sure you want to delete user: ${userIdentifier}?`)) {
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { 'X-Admin-Key': adminKey }
      });
      
      if (response.ok) {
        alert(`User ${userIdentifier} deleted successfully`);
        await loadUsers(); // Reload users list
      } else {
        const error = await response.json();
        alert(`Error deleting user: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error deleting user:', error);
      alert('Error deleting user');
    }
    setLoading(false);
  };

  const loadUpcomingEvents = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/upcoming-events?days=7`, {
        headers: { 'X-Admin-Key': adminKey }
      });
      if (response.ok) {
        const data = await response.json();
        setUpcomingEvents(data.events);
      }
    } catch (error) {
      console.error('Error loading upcoming events:', error);
    }
    setLoading(false);
  };

  const loadSocieties = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/societies-detailed`, {
        headers: { 'X-Admin-Key': adminKey }
      });
      if (response.ok) {
        const data = await response.json();
        setSocieties(data.societies);
      }
    } catch (error) {
      console.error('Error loading societies:', error);
    }
    setLoading(false);
  };

  const sendReminder = async (eventId: string) => {
    setLoading(true);
    setMessage('Sending reminder...');
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/event/${eventId}/send-reminder`, {
        method: 'POST',
        headers: { 'X-Admin-Key': adminKey }
      });
      if (response.ok) {
        const data = await response.json();
        setMessage(`✅ ${data.message} (${data.whatsapp_sent} WhatsApp, ${data.email_sent} Email)`);
        loadUpcomingEvents();
      } else {
        setMessage('❌ Failed to send reminder');
      }
    } catch (error) {
      setMessage('❌ Error sending reminder');
    }
    setLoading(false);
  };

  const toggleSociety = async (societyId: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/societies/${societyId}/toggle`, {
        method: 'POST',
        headers: { 'X-Admin-Key': adminKey }
      });
      if (response.ok) {
        const data = await response.json();
        setMessage(`✅ ${data.message}`);
        loadSocieties();
      } else {
        setMessage('❌ Failed to toggle society');
      }
    } catch (error) {
      setMessage('❌ Error toggling society');
    }
    setLoading(false);
  };

  const deleteEvent = async (eventId: string, eventTitle: string) => {
    if (!confirm(`Are you sure you want to delete "${eventTitle}"?`)) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/event/${eventId}`, {
        method: 'DELETE',
        headers: { 'X-Admin-Key': adminKey }
      });
      if (response.ok) {
        setMessage('✅ Event deleted successfully');
        loadUpcomingEvents();
      } else {
        setMessage('❌ Failed to delete event');
      }
    } catch (error) {
      setMessage('❌ Error deleting event');
    }
    setLoading(false);
  };

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const [logsRes, statsRes] = await Promise.all([
        fetch(`${BASE_URL}/api/v1/admin/notification-logs?limit=100`, {
          headers: { 'X-Admin-Key': adminKey }
        }),
        fetch(`${BASE_URL}/api/v1/admin/notification-stats?days=7`, {
          headers: { 'X-Admin-Key': adminKey }
        })
      ]);
      
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setNotificationLogs(logsData.logs);
      }
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setNotificationStats(statsData);
      }
    } catch (error) {
      console.error('Error loading notifications:', error);
    }
    setLoading(false);
  };

  const loadSystemHealth = async () => {
    setLoading(true);
    try {
      const [healthRes, errorsRes] = await Promise.all([
        fetch(`${BASE_URL}/api/v1/admin/system-health`, {
          headers: { 'X-Admin-Key': adminKey }
        }),
        fetch(`${BASE_URL}/api/v1/admin/error-logs?limit=50`, {
          headers: { 'X-Admin-Key': adminKey }
        })
      ]);
      
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setSystemHealth(healthData);
      }
      if (errorsRes.ok) {
        const errorsData = await errorsRes.json();
        setErrorLogs(errorsData.errors);
      }
    } catch (error) {
      console.error('Error loading system health:', error);
    }
    setLoading(false);
  };

  const retryFailedNotifications = async () => {
    if (!confirm('Retry all failed notifications from the last 24 hours?')) return;
    
    setLoading(true);
    setMessage('Retrying failed notifications...');
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/retry-failed-notifications?hours=24`, {
        method: 'POST',
        headers: { 'X-Admin-Key': adminKey }
      });
      if (response.ok) {
        const data = await response.json();
        setMessage(`✅ ${data.message}`);
        loadNotifications();
      } else {
        setMessage('❌ Failed to retry notifications');
      }
    } catch (error) {
      setMessage('❌ Error retrying notifications');
    }
    setLoading(false);
  };

  const triggerScrape = async (societyHandle?: string) => {
    setLoading(true);
    setMessage('Scraping in progress...');
    try {
      const url = societyHandle
        ? `${BASE_URL}/api/v1/admin/scrape-now?society_handle=${societyHandle}`
        : `${BASE_URL}/api/v1/admin/scrape-now`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'X-Admin-Key': adminKey }
      });
      
      if (response.ok) {
        const data = await response.json();
        setMessage(`✅ ${data.message}`);
        loadDashboardData(adminKey);
        loadScrapingLogs();
      } else {
        setMessage('❌ Scraping failed');
      }
    } catch (error) {
      setMessage('❌ Error triggering scrape');
    }
    setLoading(false);
  };

  const addSociety = async () => {
    if (!newSociety.name || !newSociety.instagram_handle) {
      setMessage('❌ Please fill in all required fields');
      return;
    }

    setLoading(true);
    setMessage('Adding society...');
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/societies`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Key': adminKey
        },
        body: JSON.stringify(newSociety)
      });

      if (response.ok) {
        const data = await response.json();
        setMessage(`✅ ${data.message}`);
        // Reset form
        setNewSociety({
          name: '',
          instagram_handle: '',
          scrape_posts: true,
          scrape_stories: false
        });
        // Reload societies list
        loadSocieties();
      } else {
        const error = await response.json();
        setMessage(`❌ ${error.detail || 'Failed to add society'}`);
      }
    } catch (error) {
      setMessage('❌ Error adding society');
      console.error('Error adding society:', error);
    }
    setLoading(false);
  };

  const loadRecentPosts = async () => {
    setLoading(true);
    try {
      const [postsRes, analyticsRes] = await Promise.all([
        fetch(`${BASE_URL}/api/v1/admin/posts/recent?limit=50&days=7`, {
          headers: { 'X-Admin-Key': adminKey }
        }),
        fetch(`${BASE_URL}/api/v1/admin/posts/analytics?days=30`, {
          headers: { 'X-Admin-Key': adminKey }
        })
      ]);
      
      if (postsRes.ok) {
        const data = await postsRes.json();
        setRecentPosts(data.posts);
      }
      if (analyticsRes.ok) {
        const data = await analyticsRes.json();
        setPostAnalytics(data);
      }
    } catch (error) {
      console.error('Error loading posts:', error);
    }
    setLoading(false);
  };

  const submitPostFeedback = async (postId: string, isCorrect: boolean, notes?: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/api/v1/admin/posts/${postId}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Key': adminKey
        },
        body: JSON.stringify({
          is_correct: isCorrect,
          notes: notes || null
        })
      });

      if (response.ok) {
        setMessage(`✅ Feedback submitted`);
        loadRecentPosts(); // Reload to show updated feedback
      } else {
        setMessage('❌ Failed to submit feedback');
      }
    } catch (error) {
      setMessage('❌ Error submitting feedback');
      console.error('Error submitting feedback:', error);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (isAuthenticated && activeTab === 'logs') {
      loadScrapingLogs();
    } else if (isAuthenticated && activeTab === 'posts') {
      loadRecentPosts();
    } else if (isAuthenticated && activeTab === 'users') {
      loadUsers();
    } else if (isAuthenticated && activeTab === 'events') {
      loadUpcomingEvents();
    } else if (isAuthenticated && activeTab === 'societies') {
      loadSocieties();
    } else if (isAuthenticated && activeTab === 'notifications') {
      loadNotifications();
    } else if (isAuthenticated && activeTab === 'health') {
      loadSystemHealth();
    }
  }, [activeTab, isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
          <h1 className="text-2xl font-bold mb-6 text-center">Admin Login</h1>
          <input
            type="password"
            placeholder="Enter Admin Key"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
            className="w-full p-3 border rounded-lg mb-4"
          />
          <button
            onClick={handleLogin}
            className="w-full bg-green-600 text-white p-3 rounded-lg hover:bg-green-700"
          >
            Login
          </button>
          {message && (
            <p className="mt-4 text-red-600 text-center">{message}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">FreeFoodUCD Admin</h1>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex space-x-4 border-b overflow-x-auto">
          {['dashboard', 'events', 'societies', 'notifications', 'health', 'logs', 'posts', 'users', 'scrape'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 font-medium whitespace-nowrap ${
                activeTab === tab
                  ? 'border-b-2 border-green-600 text-green-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {message && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            {message}
          </div>
        )}

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard title="Users" stats={stats.users} color="blue" />
            <StatCard title="Societies" stats={stats.societies} color="green" />
            <StatCard title="Events" stats={stats.events} color="purple" />
            <StatCard title="Posts" stats={stats.posts} color="orange" />
            <div className="col-span-full">
              <ScrapingStatus scraping={stats.scraping} onRefresh={() => loadDashboardData(adminKey)} />
            </div>
          </div>
        )}

        {/* Upcoming Events Tab */}
        {activeTab === 'events' && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold">Upcoming Events (Next 7 Days)</h2>
              <button
                onClick={loadUpcomingEvents}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Refresh
              </button>
            </div>
            <div className="divide-y divide-gray-200">
              {upcomingEvents.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  No upcoming events in the next 7 days
                </div>
              ) : (
                upcomingEvents.map((event) => (
                  <div key={event.id} className="p-4 hover:bg-gray-50">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg">{event.title}</h3>
                        <p className="text-sm text-gray-600">
                          {event.society_name} (@{event.society_handle})
                        </p>
                      </div>
                      <div className="flex gap-2">
                        {event.hours_until < 24 && (
                          <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full">
                            {event.hours_until < 1 ? 'Starting Soon!' : `${Math.floor(event.hours_until)}h away`}
                          </span>
                        )}
                        {event.reminder_sent ? (
                          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                            ✅ Reminder Sent
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                            ⏰ Reminder Pending
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 mb-3 text-sm">
                      <div>
                        <span className="text-gray-600">📅 Start:</span>
                        <span className="ml-2 font-medium">
                          {new Date(event.start_time).toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-600">📍 Location:</span>
                        <span className="ml-2 font-medium">{event.location || 'TBA'}</span>
                      </div>
                      <div>
                        <span className="text-gray-600">👥 Users to notify:</span>
                        <span className="ml-2 font-medium">{event.users_to_notify}</span>
                      </div>
                      <div>
                        <span className="text-gray-600">🎯 Confidence:</span>
                        <span className="ml-2 font-medium">{(event.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>

                    {event.description && (
                      <p className="text-sm text-gray-700 mb-3">{event.description}</p>
                    )}

                    <div className="flex gap-2">
                      <button
                        onClick={() => sendReminder(event.id)}
                        disabled={loading}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:bg-gray-400"
                      >
                        Send Reminder Now
                      </button>
                      <button
                        onClick={() => deleteEvent(event.id, event.title)}
                        disabled={loading}
                        className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:bg-gray-400"
                      >
                        Delete Event
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Societies Management Tab */}
        {activeTab === 'societies' && (
          <div className="space-y-6">
            {/* Add Society Form */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Add New Society</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Society Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., UCD Computer Science Society"
                    value={newSociety.name}
                    onChange={(e) => setNewSociety({...newSociety, name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Instagram Handle
                  </label>
                  <div className="flex">
                    <span className="inline-flex items-center px-3 rounded-l-lg border border-r-0 border-gray-300 bg-gray-50 text-gray-500 text-sm">
                      @
                    </span>
                    <input
                      type="text"
                      placeholder="ucdcompsoc"
                      value={newSociety.instagram_handle}
                      onChange={(e) => setNewSociety({...newSociety, instagram_handle: e.target.value})}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-r-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
                <div className="flex items-end">
                  <button
                    onClick={addSociety}
                    disabled={loading || !newSociety.name || !newSociety.instagram_handle}
                    className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                  >
                    Add Society
                  </button>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newSociety.scrape_posts}
                    onChange={(e) => setNewSociety({...newSociety, scrape_posts: e.target.checked})}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-gray-700">Scrape Posts</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newSociety.scrape_stories}
                    onChange={(e) => setNewSociety({...newSociety, scrape_stories: e.target.checked})}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-gray-700">Scrape Stories</span>
                </label>
              </div>
            </div>

            {/* Societies List */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b flex justify-between items-center">
                <h2 className="text-lg font-semibold">All Societies ({societies.length})</h2>
                <button
                  onClick={loadSocieties}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Refresh
                </button>
              </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Society</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Handle</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Posts</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Events</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Success Rate</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Check</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {societies.map((society) => (
                    <tr key={society.id} className={!society.is_active ? 'bg-gray-50' : ''}>
                      <td className="px-4 py-3 text-sm font-medium">{society.name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">@{society.instagram_handle}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          society.is_active 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {society.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">{society.stats.total_posts}</td>
                      <td className="px-4 py-3 text-sm">{society.stats.total_events}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`font-medium ${
                          society.stats.success_rate >= 80 ? 'text-green-600' :
                          society.stats.success_rate >= 50 ? 'text-yellow-600' :
                          'text-red-600'
                        }`}>
                          {society.stats.success_rate}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {society.last_post_check 
                          ? new Date(society.last_post_check).toLocaleDateString()
                          : 'Never'}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <button
                          onClick={() => toggleSociety(society.id)}
                          disabled={loading}
                          className={`px-3 py-1 text-white text-xs rounded hover:opacity-80 disabled:bg-gray-400 ${
                            society.is_active ? 'bg-red-600' : 'bg-green-600'
                          }`}
                        >
                          {society.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            </div>
          </div>
        )}

        {/* Notifications Tab */}
        {activeTab === 'notifications' && (
          <div className="space-y-6">
            {/* Stats Cards */}
            {notificationStats && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm text-gray-600 mb-2">Total Sent (7 days)</h3>
                  <p className="text-2xl font-bold text-gray-900">{notificationStats.total_sent}</p>
                </div>
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm text-gray-600 mb-2">Delivery Rate</h3>
                  <p className="text-2xl font-bold text-green-600">{notificationStats.delivery_rate}%</p>
                </div>
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm text-gray-600 mb-2">By Channel</h3>
                  <p className="text-sm">📱 WhatsApp: {notificationStats.by_channel.whatsapp}</p>
                  <p className="text-sm">📧 Email: {notificationStats.by_channel.email}</p>
                </div>
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm text-gray-600 mb-2">Recent Failures</h3>
                  <p className="text-2xl font-bold text-red-600">{notificationStats.recent_failures}</p>
                  {notificationStats.recent_failures > 0 && (
                    <button
                      onClick={retryFailedNotifications}
                      disabled={loading}
                      className="mt-2 text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
                    >
                      Retry Failed
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Notification Logs */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b flex justify-between items-center">
                <h2 className="text-lg font-semibold">Notification Logs (Last 100)</h2>
                <button
                  onClick={loadNotifications}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Refresh
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Event</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Society</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Channel</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Error</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {notificationLogs.map((log) => (
                      <tr key={log.id}>
                        <td className="px-4 py-3 text-sm">{new Date(log.sent_at).toLocaleString()}</td>
                        <td className="px-4 py-3 text-sm">{log.event_title}</td>
                        <td className="px-4 py-3 text-sm">{log.society_name}</td>
                        <td className="px-4 py-3 text-sm text-xs">
                          {log.notification_type === 'email' ? log.user_email : log.user_phone}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {log.notification_type === 'whatsapp' ? '📱 WhatsApp' : '📧 Email'}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            log.status === 'sent' ? 'bg-green-100 text-green-800' : 
                            log.status === 'failed' ? 'bg-red-100 text-red-800' :
                            'bg-yellow-100 text-yellow-800'
                          }`}>
                            {log.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-red-600 text-xs max-w-xs truncate">
                          {log.error_message || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* System Health Tab */}
        {activeTab === 'health' && (
          <div className="space-y-6">
            {/* Health Status Cards */}
            {systemHealth && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm text-gray-600 mb-2">Database</h3>
                  <p className={`text-lg font-bold ${
                    systemHealth.database === 'healthy' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {systemHealth.database === 'healthy' ? '🟢 Healthy' : '🔴 Unhealthy'}
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm text-gray-600 mb-2">Celery Worker</h3>
                  <p className={`text-lg font-bold ${
                    systemHealth.celery_worker === 'healthy' ? 'text-green-600' :
                    systemHealth.celery_worker === 'warning' ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {systemHealth.celery_worker === 'healthy' ? '🟢 Healthy' :
                     systemHealth.celery_worker === 'warning' ? '🟡 Warning' :
                     '🔴 ' + systemHealth.celery_worker}
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm text-gray-600 mb-2">Celery Beat</h3>
                  <p className={`text-lg font-bold ${
                    systemHealth.celery_beat === 'healthy' ? 'text-green-600' :
                    systemHealth.celery_beat === 'warning' ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {systemHealth.celery_beat === 'healthy' ? '🟢 Healthy' :
                     systemHealth.celery_beat === 'warning' ? '🟡 Warning' :
                     '🔴 ' + systemHealth.celery_beat}
                  </p>
                </div>
              </div>
            )}

            {/* Services Status */}
            {systemHealth && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4">External Services</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="font-medium">Apify (Scraping)</span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      systemHealth.services.apify === 'configured' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {systemHealth.services.apify}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="font-medium">Twilio (WhatsApp)</span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      systemHealth.services.twilio === 'configured' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {systemHealth.services.twilio}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="font-medium">Resend (Email)</span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      systemHealth.services.resend === 'configured' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {systemHealth.services.resend}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Error Logs */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b flex justify-between items-center">
                <h2 className="text-lg font-semibold">Recent Errors (Last 50)</h2>
                <button
                  onClick={loadSystemHealth}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Refresh
                </button>
              </div>
              <div className="divide-y divide-gray-200">
                {errorLogs.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    No recent errors 🎉
                  </div>
                ) : (
                  errorLogs.map((error, index) => (
                    <div key={index} className="p-4 hover:bg-gray-50">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            error.type === 'scraping' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                          }`}>
                            {error.type}
                          </span>
                          <span className="ml-2 text-sm text-gray-600">{error.source}</span>
                        </div>
                        <span className="text-xs text-gray-500">{new Date(error.timestamp).toLocaleString()}</span>
                      </div>
                      <p className="text-sm text-red-600 mb-1">{error.error}</p>
                      <p className="text-xs text-gray-500">{error.details}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Scraping Logs Tab */}
        {activeTab === 'logs' && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold">Scraping Logs</h2>
              <button
                onClick={loadScrapingLogs}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Refresh
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Society</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Items</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td className="px-4 py-3 text-sm">{new Date(log.created_at).toLocaleString()}</td>
                      <td className="px-4 py-3 text-sm">@{log.society_handle}</td>
                      <td className="px-4 py-3 text-sm">{log.scrape_type}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          log.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {log.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">{log.items_found}</td>
                      <td className="px-4 py-3 text-sm">{log.duration_ms}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Posts Review Tab */}
        {activeTab === 'posts' && (
          <div className="space-y-6">
            {/* Analytics Cards */}
            {postAnalytics && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm text-gray-600 mb-2">Accuracy (30 days)</h3>
                  <p className="text-2xl font-bold text-green-600">{postAnalytics.accuracy}%</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {postAnalytics.correct_count}/{postAnalytics.total_reviewed} correct
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm text-gray-600 mb-2">Review Rate</h3>
                  <p className="text-2xl font-bold text-blue-600">{postAnalytics.review_rate.toFixed(1)}%</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {postAnalytics.total_reviewed}/{postAnalytics.total_posts} reviewed
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm text-gray-600 mb-2">Classification Errors</h3>
                  <p className="text-2xl font-bold text-red-600">{postAnalytics.classification_errors}</p>
                  <p className="text-xs text-gray-500 mt-1">False positives/negatives</p>
                </div>
                <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm text-gray-600 mb-2">Extraction Errors</h3>
                  <p className="text-2xl font-bold text-orange-600">{postAnalytics.extraction_errors}</p>
                  <p className="text-xs text-gray-500 mt-1">Date/time/location issues</p>
                </div>
              </div>
            )}

            {/* Posts List */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b flex justify-between items-center">
                <div>
                  <h2 className="text-lg font-semibold">Recent Posts (Last 7 Days)</h2>
                  <p className="text-sm text-gray-600">Review NLP classification and extraction accuracy</p>
                </div>
                <button
                  onClick={loadRecentPosts}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Refresh
                </button>
              </div>
              <div className="divide-y divide-gray-200">
                {recentPosts.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    No posts found. Try scraping some societies first.
                  </div>
                ) : (
                  recentPosts.map((post) => (
                <div key={post.id} className="p-4 hover:bg-gray-50 border-b">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <span className="font-semibold">{post.society_name}</span>
                      <span className="text-gray-500 text-sm ml-2">@{post.society_handle}</span>
                      <span className="text-gray-400 text-xs ml-2">
                        {new Date(post.detected_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      {post.is_free_food && (
                        <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">✅ Free Food</span>
                      )}
                      {!post.is_free_food && post.processed && (
                        <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full">❌ Rejected</span>
                      )}
                      {post.event_created && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">📅 Event Created</span>
                      )}
                      {post.feedback_submitted && (
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">✓ Reviewed</span>
                      )}
                    </div>
                  </div>
                  
                  <p className="text-sm text-gray-700 mb-3 line-clamp-3">{post.caption}</p>
                  
                  {post.event && (
                    <div className="bg-purple-50 rounded-lg p-3 mb-3">
                      <p className="text-sm font-semibold text-purple-900 mb-1">📅 {post.event.title}</p>
                      <div className="text-xs text-purple-700 space-y-1">
                        {post.event.start_time && (
                          <p>🕒 {new Date(post.event.start_time).toLocaleString()}</p>
                        )}
                        {post.event.location && (
                          <p>📍 {post.event.location}</p>
                        )}
                        <p>🎯 Confidence: {(post.event.confidence_score * 100).toFixed(0)}%</p>
                        {post.event.notified && (
                          <p className="text-green-700">✅ Users notified</p>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {post.feedback && (
                    <div className={`rounded-lg p-2 mb-3 text-xs ${
                      post.feedback.is_correct ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
                    }`}>
                      {post.feedback.is_correct ? '✅ Marked as correct' : '❌ Marked as incorrect'}
                      {post.feedback.notes && <p className="mt-1">Note: {post.feedback.notes}</p>}
                    </div>
                  )}
                  
                  <div className="flex gap-2 items-center">
                    {!post.feedback_submitted && (
                      <>
                        <button
                          onClick={() => submitPostFeedback(post.id, true)}
                          disabled={loading}
                          className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:bg-gray-400"
                        >
                          ✅ Correct
                        </button>
                        <button
                          onClick={() => {
                            const notes = prompt('What was wrong? (optional)');
                            submitPostFeedback(post.id, false, notes || undefined);
                          }}
                          disabled={loading}
                          className="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700 disabled:bg-gray-400"
                        >
                          ❌ Wrong
                        </button>
                      </>
                    )}
                    <a
                      href={post.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-auto text-blue-600 hover:underline text-xs"
                    >
                      View on Instagram →
                    </a>
                  </div>
                </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold">Users ({users.length})</h2>
              <button
                onClick={loadUsers}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Refresh
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Phone</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">WhatsApp</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email Verified</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Joined</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td className="px-4 py-3 text-sm">{user.email || '-'}</td>
                      <td className="px-4 py-3 text-sm">{user.phone_number || '-'}</td>
                      <td className="px-4 py-3 text-sm">
                        {user.whatsapp_verified ? '✅' : '❌'}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {user.email_verified ? '✅' : '❌'}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          user.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">{new Date(user.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-3 text-sm">
                        <button
                          onClick={() => deleteUser(user.id, user.email || user.phone_number || 'user')}
                          className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-xs"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Scrape Tab */}
        {activeTab === 'scrape' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Manual Scraping</h2>
              <div className="space-y-4">
                <button
                  onClick={() => triggerScrape()}
                  disabled={loading}
                  className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400"
                >
                  {loading ? 'Scraping...' : '🔄 Scrape All Societies Now'}
                </button>
                <div className="text-sm text-gray-600">
                  <p>This will scrape the latest posts from all active societies.</p>
                  <p className="mt-2">⏰ Automatic scraping runs daily at 9 AM</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Test Single Society</h2>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="e.g., ucdlawsoc"
                  id="society-handle"
                  className="flex-1 p-3 border rounded-lg"
                />
                <button
                  onClick={() => {
                    const input = document.getElementById('society-handle') as HTMLInputElement;
                    if (input.value) triggerScrape(input.value);
                  }}
                  disabled={loading}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
                >
                  Test Scrape
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ title, stats, color }: { title: string; stats: any; color: string }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-gray-500 text-sm font-medium mb-2">{title}</h3>
      <div className="space-y-2">
        {Object.entries(stats).map(([key, value]) => (
          <div key={key} className="flex justify-between items-center">
            <span className="text-sm text-gray-600 capitalize">{key.replace('_', ' ')}</span>
            <span className={`text-lg font-semibold ${colors[color as keyof typeof colors]}`}>
              {value as number}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScrapingStatus({ scraping, onRefresh }: { scraping: any; onRefresh: () => void }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Scraping Status</h3>
        <button
          onClick={onRefresh}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
        >
          Refresh
        </button>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <p className="text-sm text-gray-600">Last 24h Attempts</p>
          <p className="text-2xl font-bold text-gray-900">{scraping.last_24h_attempts}</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Success Rate</p>
          <p className="text-2xl font-bold text-green-600">{scraping.success_rate}%</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Last Scrape</p>
          <p className="text-sm font-medium text-gray-900">
            {scraping.last_scrape ? new Date(scraping.last_scrape).toLocaleString() : 'Never'}
          </p>
        </div>
      </div>
    </div>
  );
}

// Made with Bob
