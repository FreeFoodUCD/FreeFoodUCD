'use client';

import { Header } from '@/components/Header';
import { EventCard, EventCardSkeleton } from '@/components/EventCard';
import EventModal from '@/components/EventModal';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Event } from '@/lib/types';
import Link from 'next/link';
import { Bell } from 'lucide-react';

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
      created_at: new Date().toISOString(),
    },
    notified: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '2',
    title: 'Free Breakfast & Career Talk',
    location: 'O\'Brien Centre for Science',
    start_time: new Date(Date.now() + 18 * 60 * 60 * 1000).toISOString(),
    end_time: new Date(Date.now() + 20 * 60 * 60 * 1000).toISOString(),
    society_id: '2',
    source_type: 'post',
    source_url: 'https://instagram.com/p/example',
    is_free_food: true,
    society: {
      id: '2',
      name: 'UCD Computer Science Society',
      instagram_handle: 'ucdcompsci',
      is_active: true,
      created_at: new Date().toISOString(),
    },
    notified: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '3',
    title: 'Taco Tuesday Social',
    location: 'Student Centre',
    start_time: new Date(Date.now() + 26 * 60 * 60 * 1000).toISOString(),
    end_time: new Date(Date.now() + 28 * 60 * 60 * 1000).toISOString(),
    society_id: '3',
    source_type: 'story',
    is_free_food: true,
    society: {
      id: '3',
      name: 'UCD Business Society',
      instagram_handle: 'ucdbusiness',
      is_active: true,
      created_at: new Date().toISOString(),
    },
    notified: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

export default function Home() {
  const [useMockData] = useState(false); // Changed to false to use real API
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch events from API
  const { data, isLoading, error } = useQuery({
    queryKey: ['events'],
    queryFn: () => api.getEvents({}),
    enabled: !useMockData,
  });

  // Fallback to mock data if API fails or returns empty
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

  return (
    <div className="min-h-screen bg-white">
      <Header />
      
      {/* Hero Section - Minimal & Playful */}
      <section className="pt-24 pb-8 px-4">
        <div className="max-w-4xl mx-auto text-center">
          {/* Playful Headline */}
          <h1 className="text-5xl md:text-7xl font-bold text-gray-900 mb-6 leading-tight">
            cuz who doesn't want <span className="text-primary">free food</span>
          </h1>

          {/* Tagline */}
          <p className="text-xl md:text-2xl text-gray-600 mb-10">
            whatsapp or email alerts
          </p>

          {/* Single CTA */}
          <Link
            href="/signup"
            className="inline-flex items-center gap-2 px-10 py-5 rounded-xl bg-primary text-white text-xl font-semibold hover:bg-primary-dark transition-all shadow-lg hover:shadow-xl hover:scale-105"
          >
            sign me up
          </Link>
        </div>
      </section>

      {/* Events Preview - Visible Without Scrolling */}
      <section className="px-4 pb-12">
        <div className="max-w-7xl mx-auto">
          {/* Section Header */}
          <div className="text-center mb-6">
            <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
              what's happening now 👀
            </h2>
          </div>

          {/* Event Grid - Show partial cards */}
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
              <p className="text-gray-600 mb-6">
                be the first to know when they drop
              </p>
              <Link
                href="/signup"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-primary text-white font-semibold hover:bg-primary-dark transition-colors"
              >
                <Bell className="w-5 h-5" />
                get notified
              </Link>
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
