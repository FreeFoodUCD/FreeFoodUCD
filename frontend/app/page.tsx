'use client';

import { Header } from '@/components/Header';
import { EventCard, EventCardSkeleton } from '@/components/EventCard';
import EventModal from '@/components/EventModal';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Event } from '@/lib/types';
import { Mail, Check, AlertCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';

// Mock data for development
const MOCK_EVENTS: Event[] = [
  {
    id: '1',
    title: 'Pizza Night & Movie Screening',
    location: 'Newman Building A105',
    start_time: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
    end_time: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(),
    society_id: '1',
    source_type: 'story',
    is_free_food: true,
    society: {
      id: '1',
      name: 'UCD Law Society',
      instagram_handle: 'ucdlawsoc',
      is_active: true,
      scrape_posts: true,
      scrape_stories: true,
      created_at: new Date().toISOString(),
    },
    notified: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

export default function Home() {
  const router = useRouter();
  const [useMockData] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Fetch events from API
  const { data, isLoading, error } = useQuery({
    queryKey: ['events'],
    queryFn: () => api.getEvents({}),
    enabled: !useMockData,
  });

  const events = useMockData || (!isLoading && !error && data?.items && data.items.length === 0)
    ? MOCK_EVENTS
    : (data?.items || []);

  const handleEventClick = (event: Event) => {
    setSelectedEvent(event);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setTimeout(() => setSelectedEvent(null), 300);
  };

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus('idle');

    try {
      await api.signup({ email });
      setSubmitStatus('success');
      setEmail('');
      // Redirect to verification page after 1 second
      setTimeout(() => {
        router.push('/signup');
      }, 1000);
    } catch (err: any) {
      setSubmitStatus('error');
      console.error('Signup error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <Header />
      
      {/* Hero Section with Email Signup */}
      <section className="pt-24 pb-12 px-4">
        <div className="max-w-4xl mx-auto text-center">
          {/* Headline */}
          <h1 className="text-5xl md:text-7xl font-bold text-gray-900 mb-6 leading-tight">
            never miss <span className="text-primary">free food</span> again
          </h1>

          {/* Tagline */}
          <p className="text-xl md:text-2xl text-gray-600 mb-10">
            instant email alerts when UCD societies post about free food
          </p>

          {/* Email Signup Form */}
          <div className="max-w-md mx-auto">
            <form onSubmit={handleEmailSubmit} className="space-y-4">
              <div className="flex gap-3">
                <div className="flex-1 relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@ucd.ie"
                    required
                    className="w-full pl-12 pr-4 py-4 rounded-xl border-2 border-gray-200 focus:border-primary focus:outline-none text-lg"
                    disabled={isSubmitting || submitStatus === 'success'}
                  />
                </div>
                <button
                  type="submit"
                  disabled={isSubmitting || submitStatus === 'success'}
                  className="px-8 py-4 rounded-xl bg-primary text-white text-lg font-semibold hover:bg-primary-dark transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'sending...' : submitStatus === 'success' ? 'sent!' : 'sign up'}
                </button>
              </div>

              {/* Status Messages */}
              {submitStatus === 'success' && (
                <div className="flex items-center gap-2 text-green-600 bg-green-50 px-4 py-3 rounded-lg">
                  <Check className="w-5 h-5" />
                  <span>check your email for verification code!</span>
                </div>
              )}

              {submitStatus === 'error' && (
                <div className="flex items-center gap-2 text-red-600 bg-red-50 px-4 py-3 rounded-lg">
                  <AlertCircle className="w-5 h-5" />
                  <span>something went wrong. try again?</span>
                </div>
              )}
            </form>

            <p className="text-sm text-gray-500 mt-4">
              free forever • no spam • unsubscribe anytime
            </p>
          </div>
        </div>
      </section>

      {/* Events Preview */}
      <section className="px-4 pb-12">
        <div className="max-w-7xl mx-auto">
          {/* Section Header */}
          <div className="text-center mb-8">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
              what's happening now 👀
            </h2>
            <p className="text-gray-600">
              recent free food events from UCD societies
            </p>
          </div>

          {/* Event Grid */}
          {isLoading && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[...Array(3)].map((_, i) => (
                <EventCardSkeleton key={i} />
              ))}
            </div>
          )}

          {error && (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">😕</div>
              <p className="text-gray-600">couldn't load events</p>
            </div>
          )}

          {!isLoading && !error && events.length === 0 && (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">🔍</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                no events right now
              </h3>
              <p className="text-gray-600">
                be the first to know when they drop
              </p>
            </div>
          )}

          {!isLoading && !error && events.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {events.map((event) => (
                <EventCard
                  key={event.id}
                  event={event}
                  onClick={() => handleEventClick(event)}
                />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Event Detail Modal */}
      <EventModal
        event={selectedEvent}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />
    </div>
  );
}

// Made with Bob
