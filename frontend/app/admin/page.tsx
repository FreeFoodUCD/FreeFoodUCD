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
  has_event: boolean;
  event_title: string | null;
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

export default function AdminDashboard() {
  const router = useRouter();
  const [adminKey, setAdminKey] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [logs, setLogs] = useState<ScrapingLog[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

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

  useEffect(() => {
    if (isAuthenticated && activeTab === 'logs') {
      loadScrapingLogs();
    } else if (isAuthenticated && activeTab === 'posts') {
      loadPosts();
    } else if (isAuthenticated && activeTab === 'users') {
      loadUsers();
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
        <div className="flex space-x-4 border-b">
          {['dashboard', 'logs', 'posts', 'users', 'scrape'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 font-medium ${
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

        {/* Posts Tab */}
        {activeTab === 'posts' && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold">Scraped Posts</h2>
              <button
                onClick={loadPosts}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Refresh
              </button>
            </div>
            <div className="divide-y divide-gray-200">
              {posts.map((post) => (
                <div key={post.id} className="p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <span className="font-semibold">{post.society_name}</span>
                      <span className="text-gray-500 text-sm ml-2">@{post.society_handle}</span>
                    </div>
                    <div className="flex gap-2">
                      {post.is_free_food && (
                        <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">Free Food</span>
                      )}
                      {post.has_event && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">Has Event</span>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">{post.caption}</p>
                  {post.event_title && (
                    <p className="text-sm text-purple-600 mb-2">📅 Event: {post.event_title}</p>
                  )}
                  <div className="flex justify-between items-center text-xs text-gray-500">
                    <span>{new Date(post.detected_at).toLocaleString()}</span>
                    <a href={post.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      View on Instagram →
                    </a>
                  </div>
                </div>
              ))}
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
