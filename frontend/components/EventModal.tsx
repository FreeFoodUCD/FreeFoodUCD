'use client';

import { Event } from '@/lib/types';
import { shareEvent } from '@/lib/utils';
import { X, MapPin, Clock, Calendar, Users, ExternalLink, Share2, Check } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

const MODAL_TITLE_ID = 'event-modal-title';

interface EventModalProps {
  event: Event | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function EventModal({ event, isOpen, onClose }: EventModalProps) {
  const [mounted, setMounted] = useState(false);
  const [shareStatus, setShareStatus] = useState<'idle' | 'copied'>('idle');
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const shareTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setMounted(true);
    return () => {
      if (shareTimerRef.current) clearTimeout(shareTimerRef.current);
    };
  }, []);

  // Body scroll lock
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Focus close button when modal opens
  useEffect(() => {
    if (isOpen) {
      closeButtonRef.current?.focus();
    }
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !event || !mounted) return null;

  const handleShare = async () => {
    const success = await shareEvent(event);
    if (success) {
      setShareStatus('copied');
      if (shareTimerRef.current) clearTimeout(shareTimerRef.current);
      shareTimerRef.current = setTimeout(() => setShareStatus('idle'), 2000);
    }
  };

  const getTimeUntilEvent = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();

    if (diffMs < 0) return 'ended';

    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) return `in ${diffMins} min`;
    if (diffHours < 24) return `in ${diffHours}h`;
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
    <div
      className="fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-4 bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={MODAL_TITLE_ID}
        className="relative w-full md:max-w-2xl bg-white rounded-t-3xl md:rounded-3xl shadow-2xl max-h-[95vh] md:max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-primary text-white p-6 md:p-8 rounded-t-3xl">
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className="absolute top-4 right-4 p-2 hover:bg-white/20 rounded-2xl transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            aria-label="Close event details"
          >
            <X className="w-6 h-6" />
          </button>

          <div className="pr-12">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/20 rounded-full text-sm font-bold mb-4">
              {event.source_type === 'story' ? '📸 Story' : '📱 Post'}
            </div>
            <h2 id={MODAL_TITLE_ID} className="text-2xl md:text-3xl font-bold mb-3 leading-tight break-words">{event.title}</h2>
            <div className="flex items-center gap-2 text-white/90 min-w-0">
              <Users className="w-5 h-5 flex-shrink-0" />
              <span className="font-semibold truncate">{event.society.name}</span>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 md:p-8 space-y-5">
          {/* Time & Date */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-start gap-3 p-4 bg-secondary/10 rounded-2xl border-2 border-secondary/20">
              <div className="p-2 bg-secondary/20 rounded-xl">
                <Clock className="w-5 h-5 text-text-light" />
              </div>
              <div>
                <p className="text-sm text-text-light font-semibold mb-1">Time</p>
                <p className="font-bold text-text text-lg">{formatTime(event.start_time)}</p>
                <p className="text-sm text-text-light font-semibold mt-1">
                  {getTimeUntilEvent(event.start_time)}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-4 bg-primary/10 rounded-2xl border-2 border-primary/20">
              <div className="p-2 bg-primary/20 rounded-xl">
                <Calendar className="w-5 h-5 text-text-light" />
              </div>
              <div>
                <p className="text-sm text-text-light font-semibold mb-1">Date</p>
                <p className="font-bold text-text">{formatDate(event.start_time)}</p>
              </div>
            </div>
          </div>

          {/* Location */}
          <div className="flex items-start gap-3 p-4 bg-accent/10 rounded-2xl border-2 border-accent/20">
            <div className="p-2 bg-accent/20 rounded-xl">
              <MapPin className="w-5 h-5 text-accent-text" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-text-light font-semibold mb-1">Location</p>
              <p className="font-bold text-text mb-2 break-words">{event.location}</p>
              <a
                href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(event.location + ' UCD')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-accent-text hover:underline font-bold"
              >
                Open in Google Maps
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Description */}
          {event.description && (
            <div className="p-4 bg-primary/5 rounded-2xl border-2 border-primary/10">
              <p className="text-sm text-text-light font-semibold mb-2">Description</p>
              <p className="text-text leading-relaxed break-words">{event.description}</p>
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
              className="flex-1 flex items-center justify-center gap-2 px-6 py-4 bg-primary text-white rounded-2xl font-bold hover:bg-primary-dark transition-all shadow-soft hover:shadow-soft-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              aria-live="polite"
            >
              {shareStatus === 'copied' ? (
                <>
                  <Check className="w-5 h-5" />
                  Copied!
                </>
              ) : (
                <>
                  <Share2 className="w-5 h-5" />
                  Share Event
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Made with Bob
