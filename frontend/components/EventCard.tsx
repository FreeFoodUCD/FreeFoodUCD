'use client';

import { Event } from '@/lib/types';
import {
  formatEventTime,
  getRelativeTime,
  isEventLive,
  isEventEndingSoon,
  getMinutesUntilEnd,
  isEventPast,
  getSocietyColor,
  shareEvent,
  cn,
} from '@/lib/utils';
import { MapPin, Clock, Share2 } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';

interface EventCardProps {
  event: Event;
  onClick?: () => void;
}

export function EventCard({ event, onClick }: EventCardProps) {
  // Use state to handle time-based values on client side only
  const [mounted, setMounted] = useState(false);
  const [shareStatus, setShareStatus] = useState<'idle' | 'copied'>('idle');
  const shareTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [timeState, setTimeState] = useState({
    isLive: false,
    isEndingSoon: false,
    isPast: false,
    minutesLeft: 0,
    relativeTime: '',
  });

  const societyColor = getSocietyColor(event.society.name);

  useEffect(() => {
    setMounted(true);
    
    const updateTimeState = () => {
      const isLive = isEventLive(event.start_time, event.end_time);
      const isEndingSoon = isEventEndingSoon(event.start_time, event.end_time);
      const isPast = isEventPast(event.start_time, event.end_time);
      const minutesLeft = isEndingSoon ? getMinutesUntilEnd(event.start_time, event.end_time) : 0;
      const relativeTime = getRelativeTime(event.created_at);

      setTimeState({
        isLive,
        isEndingSoon,
        isPast,
        minutesLeft,
        relativeTime,
      });
    };

    updateTimeState();
    
    // Update every minute
    const interval = setInterval(updateTimeState, 60000);
    
    return () => clearInterval(interval);
  }, [event.start_time, event.end_time, event.created_at]);

  const { isLive, isEndingSoon, isPast, minutesLeft, relativeTime } = timeState;

  // Get food emoji based on event title
  const getFoodEmoji = () => {
    const title = event.title.toLowerCase();
    if (title.includes('pizza')) return '🍕';
    if (title.includes('sandwich') || title.includes('sub')) return '🥪';
    if (title.includes('donut') || title.includes('doughnut')) return '🍩';
    if (title.includes('burger')) return '🍔';
    if (title.includes('taco')) return '🌮';
    if (title.includes('coffee') || title.includes('tea')) return '☕';
    if (title.includes('cake') || title.includes('dessert')) return '🍰';
    if (title.includes('cookie')) return '🍪';
    return '🍕'; // default
  };

  useEffect(() => {
    return () => {
      if (shareTimerRef.current) clearTimeout(shareTimerRef.current);
    };
  }, []);

  const handleShare = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const success = await shareEvent(event);
    if (success) {
      setShareStatus('copied');
      if (shareTimerRef.current) clearTimeout(shareTimerRef.current);
      shareTimerRef.current = setTimeout(() => setShareStatus('idle'), 2000);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
      className={cn(
        'bg-white rounded-3xl shadow-md hover:shadow-lg transition-all duration-300 cursor-pointer overflow-hidden',
        'border-2 border-gray-100 hover:border-primary/20',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
        isLive && 'ring-2 ring-primary ring-offset-2 ring-offset-white',
        isEndingSoon && 'ring-2 ring-secondary ring-offset-2 ring-offset-white',
        isPast && 'opacity-60'
      )}
      aria-label={`${event.title} — ${event.society.name}, ${formatEventTime(event.start_time)}`}
    >
      <div className="p-5 md:p-6">
        {/* Header with food emoji and badges */}
        <div className="flex items-start gap-3 mb-4">
          <div className="text-4xl md:text-5xl flex-shrink-0">
            {getFoodEmoji()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              {/* Live Badge */}
              {isLive && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-primary text-white animate-pulse-ring">
                  <span className="w-2 h-2 rounded-full bg-white"></span>
                  LIVE NOW
                </span>
              )}

              {/* Ending Soon Badge */}
              {isEndingSoon && (
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-secondary text-text">
                  ⏰ {minutesLeft}m left
                </span>
              )}

              {/* Members Only Badge */}
              {event.members_only && (
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                  🔒 Members only
                </span>
              )}

              {/* Time ago */}
              {mounted && !isLive && (
                <span className="text-xs font-medium text-text-lighter">
                  {relativeTime}
                </span>
              )}
            </div>

            {/* Event Title */}
            <h3 className="text-lg md:text-xl font-bold text-text leading-tight line-clamp-2 mb-2">
              {event.title}
            </h3>
          </div>
        </div>

        {/* Society */}
        <div className="flex items-center gap-3 mb-4 p-3 bg-gray-50 rounded-2xl border border-gray-100 min-w-0">
          <div
            className="w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center text-white font-bold text-sm shadow-sm"
            style={{ backgroundColor: societyColor }}
          >
            {event.society.name.charAt(0)}
          </div>
          <span className="text-sm font-bold text-text truncate">
            {event.society.name}
          </span>
        </div>

        {/* Details */}
        <div className="space-y-3 mb-4">
          {/* Location */}
          <div className="flex items-start gap-3 text-sm text-text-light">
            <MapPin className="w-5 h-5 mt-0.5 text-primary flex-shrink-0" />
            <span className="line-clamp-1 font-medium">{event.location}</span>
          </div>

          {/* Time */}
          <div className="flex items-center gap-3 text-sm text-text-light">
            <Clock className="w-5 h-5 text-primary flex-shrink-0" />
            <span className="font-medium">
              {isLive ? '🔥 Happening Now!' : formatEventTime(event.start_time)}
            </span>
          </div>
        </div>

        {/* Description (if available) */}
        {event.description && (
          <p className="text-sm text-text-light line-clamp-2 mb-4 leading-relaxed">
            {event.description}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-4 border-t-2 border-gray-100">
          <span className="text-xs font-semibold text-text-lighter">
            📸 {event.source_type === 'story' ? 'Story' : 'Post'}
          </span>
          <button
            onClick={handleShare}
            className="flex items-center gap-1.5 p-2 text-text-lighter hover:text-primary transition-colors rounded-xl hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            aria-label={shareStatus === 'copied' ? 'Copied to clipboard' : 'Share event'}
          >
            {shareStatus === 'copied' ? (
              <span className="text-xs font-semibold text-accent-text">Copied!</span>
            ) : (
              <Share2 className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// Loading skeleton
export function EventCardSkeleton() {
  return (
    <div className="bg-white rounded-3xl shadow-soft p-5 md:p-6 animate-pulse">
      <div className="flex items-start gap-3 mb-4">
        <div className="w-12 h-12 md:w-14 md:h-14 bg-gray-200 rounded-2xl"></div>
        <div className="flex-1">
          <div className="h-5 bg-gray-200 rounded-xl w-24 mb-2"></div>
          <div className="h-6 bg-gray-200 rounded-xl w-3/4"></div>
        </div>
      </div>
      <div className="flex items-center gap-3 mb-4 p-3 bg-gray-100 rounded-2xl">
        <div className="w-10 h-10 rounded-full bg-gray-200"></div>
        <div className="h-4 bg-gray-200 rounded-xl w-32"></div>
      </div>
      <div className="space-y-3 mb-4">
        <div className="h-4 bg-gray-200 rounded-xl w-full"></div>
        <div className="h-4 bg-gray-200 rounded-xl w-2/3"></div>
      </div>
    </div>
  );
}

// Made with Bob
