'use client';

import { Event } from '@/lib/types';
import { X, MapPin, Clock, Calendar, Users, ExternalLink, Share2 } from 'lucide-react';
import { useEffect, useState } from 'react';

interface EventModalProps {
  event: Event | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function EventModal({ event, isOpen, onClose }: EventModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen || !event || !mounted) return null;

  const handleShare = async () => {
    const shareData = {
      title: event.title,
      text: `🍕 Free Food at ${event.society.name}!\n📍 ${event.location}\n🕒 ${event.start_time}`,
      url: window.location.href,
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch (err) {
        console.log('Share cancelled');
      }
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(
        `${shareData.text}\n${shareData.url}`
      );
      alert('Event details copied to clipboard!');
    }
  };

  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();

    if (diffMs < 0) return 'ended';

    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) return `in ${diffMins} minutes`;
    if (diffHours < 24) return `in ${diffHours} hours`;
    if (diffDays === 0) return 'today';
    if (diffDays === 1) return 'tomorrow';
    return `in ${diffDays} days`;
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('en-IE', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IE', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-4 bg-black/50 backdrop-blur-sm">
      <div className="relative w-full md:max-w-2xl bg-white rounded-t-3xl md:rounded-3xl shadow-2xl max-h-[95vh] md:max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-primary text-white p-6 md:p-8 rounded-t-3xl">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 hover:bg-white/20 rounded-2xl transition-all"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
          
          <div className="pr-12">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/20 rounded-full text-sm font-bold mb-4">
              {event.source_type === 'story' ? '📸 Story' : '📱 Post'}
            </div>
            <h2 className="text-2xl md:text-3xl font-bold mb-3 leading-tight">{event.title}</h2>
            <div className="flex items-center gap-2 text-white/90">
              <Users className="w-5 h-5" />
              <span className="font-semibold">{event.society.name}</span>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 md:p-8 space-y-5">
          {/* Time & Date */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-start gap-3 p-4 bg-secondary/10 rounded-2xl border-2 border-secondary/20">
              <div className="p-2 bg-secondary/20 rounded-xl">
                <Clock className="w-5 h-5 text-secondary-dark" />
              </div>
              <div>
                <p className="text-sm text-text-light font-semibold mb-1">Time</p>
                <p className="font-bold text-text text-lg">{formatTime(event.start_time)}</p>
                <p className="text-sm text-secondary-dark font-bold mt-1">
                  {getRelativeTime(event.start_time)}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-4 bg-primary/10 rounded-2xl border-2 border-primary/20">
              <div className="p-2 bg-primary/20 rounded-xl">
                <Calendar className="w-5 h-5 text-primary-dark" />
              </div>
              <div>
                <p className="text-sm text-text-light font-semibold mb-1">Date</p>
                <p className="font-bold text-text">{formatDate(event.start_time)}</p>
              </div>
            </div>
          </div>

          {/* Location */}
          <div className="flex items-start gap-3 p-4 bg-success/10 rounded-2xl border-2 border-success/20">
            <div className="p-2 bg-success/20 rounded-xl">
              <MapPin className="w-5 h-5 text-success-dark" />
            </div>
            <div className="flex-1">
              <p className="text-sm text-text-light font-semibold mb-1">Location</p>
              <p className="font-bold text-text mb-2">{event.location}</p>
              <a
                href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(event.location + ' UCD')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-success-dark hover:text-success font-bold"
              >
                Open in Google Maps
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Description */}
          {event.description && (
            <div className="p-4 bg-cream rounded-2xl border-2 border-primary/10">
              <p className="text-sm text-text-light font-semibold mb-2">Description</p>
              <p className="text-text leading-relaxed">{event.description}</p>
            </div>
          )}

          {/* Source Link */}
          {event.source_url && (
            <div className="p-4 bg-primary/5 rounded-2xl border-2 border-primary/10">
              <p className="text-sm text-text-light font-semibold mb-2">Source</p>
              <a
                href={event.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-primary hover:text-primary-dark font-bold"
              >
                View original post on Instagram
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4">
            <button
              onClick={handleShare}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-4 bg-primary text-white rounded-2xl font-bold hover:bg-primary-dark transition-all shadow-soft hover:shadow-soft-hover"
            >
              <Share2 className="w-5 h-5" />
              Share Event
            </button>
            <button
              onClick={onClose}
              className="px-6 py-4 bg-cream text-text rounded-2xl font-bold hover:bg-primary/10 transition-all border-2 border-primary/20"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Made with Bob
