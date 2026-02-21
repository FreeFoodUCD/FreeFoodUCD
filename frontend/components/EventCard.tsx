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
  cn,
} from '@/lib/utils';
import { MapPin, Clock, Share2 } from 'lucide-react';
import { useState, useEffect } from 'react';

interface EventCardProps {
  event: Event;
  onClick?: () => void;
}

export function EventCard({ event, onClick }: EventCardProps) {
  // Use state to handle time-based values on client side only
  const [mounted, setMounted] = useState(false);
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

  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-white rounded-2xl shadow-card hover:shadow-card-hover transition-all duration-200 cursor-pointer overflow-hidden',
        'border-2 border-transparent',
        isLive && 'border-l-4 border-l-danger',
        isEndingSoon && 'border-l-4 border-l-warning',
        isPast && 'opacity-60'
      )}
    >
      <div className="p-4">
        {/* Header with badges */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              {/* Free Food Badge */}
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary">
                Free Food
              </span>

              {/* Live Badge */}
              {isLive && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-danger text-white animate-pulse-ring">
                  <span className="w-1.5 h-1.5 rounded-full bg-white"></span>
                  LIVE
                </span>
              )}

              {/* Ending Soon Badge */}
              {isEndingSoon && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-warning text-gray-900">
                  ⚠️ {minutesLeft}m left
                </span>
              )}

              {/* Time ago */}
              {mounted && (
                <span className="text-xs text-gray-500">
                  {relativeTime}
                </span>
              )}
            </div>

            {/* Event Title */}
            <h3 className="text-lg font-bold text-gray-900 leading-tight line-clamp-2">
              {event.title}
            </h3>
          </div>
        </div>

        {/* Society */}
        <div className="flex items-center gap-2.5 mb-3">
          <div
            className="w-9 h-9 rounded-full flex items-center justify-center text-white font-semibold text-sm shadow-sm"
            style={{ backgroundColor: societyColor }}
          >
            {event.society.name.charAt(0)}
          </div>
          <span className="text-sm font-semibold text-gray-700">
            {event.society.name}
          </span>
        </div>

        {/* Details */}
        <div className="space-y-2 mb-3">
          {/* Location */}
          <div className="flex items-start gap-2.5 text-sm text-gray-600">
            <MapPin className="w-4 h-4 mt-0.5 text-gray-400 flex-shrink-0" />
            <span className="line-clamp-1">{event.location}</span>
          </div>

          {/* Time */}
          <div className="flex items-center gap-2.5 text-sm text-gray-600">
            <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span>
              {isLive ? 'Happening Now!' : formatEventTime(event.start_time)}
            </span>
          </div>
        </div>

        {/* Description (if available) */}
        {event.description && (
          <p className="text-sm text-gray-600 line-clamp-2 mb-3">
            {event.description}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100">
          <span className="text-xs text-gray-500">
            From Instagram {event.source_type === 'story' ? 'Story' : 'Post'}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              // Share functionality
            }}
            className="p-1.5 text-gray-400 hover:text-primary transition-colors rounded-lg hover:bg-gray-50"
            aria-label="Share event"
          >
            <Share2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// Loading skeleton
export function EventCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl shadow-card p-4 animate-pulse">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="h-5 bg-gray-200 rounded w-24 mb-2"></div>
          <div className="h-6 bg-gray-200 rounded w-3/4"></div>
        </div>
      </div>
      <div className="flex items-center gap-2.5 mb-3">
        <div className="w-9 h-9 rounded-full bg-gray-200"></div>
        <div className="h-4 bg-gray-200 rounded w-32"></div>
      </div>
      <div className="space-y-2 mb-3">
        <div className="h-4 bg-gray-200 rounded w-full"></div>
        <div className="h-4 bg-gray-200 rounded w-2/3"></div>
      </div>
    </div>
  );
}

// Made with Bob
