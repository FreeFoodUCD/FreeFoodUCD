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
import Image from 'next/image';


export default function Home() {
  const router = useRouter();
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Fetch events from API (next 24 hours)
  const { data, isLoading, error } = useQuery({
    queryKey: ['events', '24h'],
    queryFn: () => api.getEvents({ date_filter: '24h' }),
  });

  const events = data?.items || [];

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
      // Redirect to verification page after 2 seconds with email in URL
      setTimeout(() => {
        router.push(`/signup?email=${encodeURIComponent(email)}`);
      }, 2000);
    } catch (err: any) {
      setSubmitStatus('error');
      console.error('Signup error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-white relative overflow-hidden">
      <Header />
      
      {/* Hero Section with Email Signup */}
      <section className="pt-24 md:pt-32 pb-20 md:pb-24 px-4 relative z-10">
        <div className="max-w-5xl mx-auto">
          {/* Headline with Logo - Left aligned */}
          <div className="flex items-center gap-3 md:gap-8 mb-8 md:mb-12">
            <h1 className="text-[2.5rem] md:text-7xl lg:text-8xl font-extrabold text-text leading-[1.1]">
              yes, it is<br />
              that serious
            </h1>
            <div className="relative w-24 h-24 md:w-[336px] md:h-[336px] lg:w-[392px] lg:h-[392px] animate-bounce-slow flex-shrink-0">
              <Image
                src="/FreeFoodUCDLogo_nobg.png"
                alt="FreeFood UCD Pizza"
                fill
                className="object-contain"
                priority
              />
            </div>
          </div>

          {/* Email Signup Form */}
          <div className="max-w-2xl mx-auto">
            {/* Tagline above form */}
            <p className="text-sm md:text-2xl text-text-light mb-6 font-medium text-center">
              get email alerts when free food drops on campus
            </p>
            
            <form onSubmit={handleEmailSubmit} className="space-y-5">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1 relative">
                  <Mail className="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-text-lighter" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="sillybilly@gmail.com"
                    required
                    className="w-full pl-14 pr-5 py-5 md:py-6 rounded-2xl border-2 border-gray-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 text-lg md:text-xl bg-white transition-all"
                    disabled={isSubmitting || submitStatus === 'success'}
                  />
                </div>
                <button
                  type="submit"
                  disabled={isSubmitting || submitStatus === 'success'}
                  className="px-10 md:px-12 py-5 md:py-6 rounded-2xl bg-accent text-white text-lg md:text-xl font-bold hover:bg-accent-dark transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap shadow-md hover:shadow-lg"
                >
                  {isSubmitting ? 'Sending...' : submitStatus === 'success' ? 'Sent ✓' : 'Join Waitlist'}
                </button>
              </div>

              {/* Status Messages */}
              {submitStatus === 'success' && (
                <div className="flex items-center gap-3 text-accent-dark bg-accent/10 px-5 py-4 rounded-2xl border-2 border-accent/30">
                  <Check className="w-6 h-6 flex-shrink-0" />
                  <span className="font-semibold text-lg">Check your email for verification code</span>
                </div>
              )}

              {submitStatus === 'error' && (
                <div className="flex items-center gap-3 text-danger-dark bg-danger/10 px-5 py-4 rounded-2xl border-2 border-danger/30">
                  <AlertCircle className="w-6 h-6 flex-shrink-0" />
                  <span className="font-semibold text-lg">Already signed up or invalid email</span>
                </div>
              )}
            </form>
          </div>
        </div>
      </section>

      {/* Events Preview */}
      <section className="px-4 pb-16 pt-8 md:pt-0">
        <div className="max-w-7xl mx-auto">
          {/* Section Header */}
          <div className="text-center mb-12 md:mb-10">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-text mb-4 md:mb-3">
              what's happening now
            </h2>
            <p className="text-lg text-text-light font-medium">
              free food events in the next 24 hours
            </p>
          </div>

          {/* Event Grid */}
          {isLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6">
              {[...Array(3)].map((_, i) => (
                <EventCardSkeleton key={i} />
              ))}
            </div>
          )}

          {error && (
            <div className="text-center py-16 bg-white rounded-3xl shadow-soft">
              <p className="text-lg text-text-light font-semibold">we're working on it :)</p>
            </div>
          )}

          {!isLoading && !error && events.length === 0 && (
            <div className="text-center py-16 bg-white rounded-3xl shadow-soft">
              <p className="text-lg text-text-light font-semibold">we're working on it :)</p>
            </div>
          )}

          {!isLoading && !error && events.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6">
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
