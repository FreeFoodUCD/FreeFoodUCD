'use client';

import { TimeFilter } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Filter } from 'lucide-react';
import { useEffect, useState } from 'react';

interface FilterBarProps {
  timeFilter: TimeFilter;
  onTimeFilterChange: (filter: TimeFilter) => void;
  selectedSocieties: string[];
  onSocietiesChange: (societies: string[]) => void;
}

export function FilterBar({
  timeFilter,
  onTimeFilterChange,
  selectedSocieties,
  onSocietiesChange,
}: FilterBarProps) {
  const [showSocietyFilter, setShowSocietyFilter] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowSocietyFilter(false);
    };
    if (showSocietyFilter) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [showSocietyFilter]);

  const timeFilters: { value: TimeFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'today', label: 'Today' },
    { value: 'tomorrow', label: 'Tomorrow' },
    { value: 'this_week', label: 'This Week' },
  ];

  return (
    <div className="sticky top-16 z-40 bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide">
          {/* Time Filters */}
          {timeFilters.map((filter) => (
            <button
              key={filter.value}
              onClick={() => onTimeFilterChange(filter.value)}
              className={cn(
                'px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap transition-all',
                timeFilter === filter.value
                  ? 'bg-primary text-white shadow-sm'
                  : 'bg-white text-text-light border border-gray-200 hover:border-primary/30'
              )}
            >
              {filter.label}
            </button>
          ))}

          {/* Society Filter Button */}
          <button
            onClick={() => setShowSocietyFilter(!showSocietyFilter)}
            className={cn(
              'px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap transition-all flex items-center gap-2',
              selectedSocieties.length > 0
                ? 'bg-primary text-white shadow-sm'
                : 'bg-white text-text-light border border-gray-200 hover:border-primary/30'
            )}
          >
            <Filter className="w-4 h-4" />
            Societies
            {selectedSocieties.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-white/20 text-xs">
                {selectedSocieties.length}
              </span>
            )}
          </button>
        </div>

        {/* Active Filters */}
        {selectedSocieties.length > 0 && (
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            <span className="text-xs text-text-lighter">Filtered by:</span>
            {selectedSocieties.map((societyId) => (
              <span
                key={societyId}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium"
              >
                Society {societyId}
                <button
                  onClick={() =>
                    onSocietiesChange(
                      selectedSocieties.filter((id) => id !== societyId)
                    )
                  }
                  className="hover:bg-primary/20 rounded-full p-0.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                  aria-label={`Remove society ${societyId} filter`}
                >
                  ×
                </button>
              </span>
            ))}
            <button
              onClick={() => onSocietiesChange([])}
              className="text-xs text-text-lighter hover:text-text-light underline"
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {/* Society Filter Modal - TODO: Implement full modal */}
      {showSocietyFilter && (
        <div
          className="fixed inset-0 bg-black/50 z-50"
          onClick={() => setShowSocietyFilter(false)}
        >
          <div
            className="absolute bottom-0 left-0 right-0 bg-white rounded-t-2xl p-6 max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold mb-4">Filter by Society</h3>
            <p className="text-sm text-text-light">
              society filtering is coming soon. for now you'll see all events from all 78 societies.
            </p>
            <button
              onClick={() => setShowSocietyFilter(false)}
              className="mt-4 w-full px-4 py-3 rounded-lg bg-primary text-white font-semibold hover:bg-primary-dark transition-all"
            >
              got it
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Made with Bob
