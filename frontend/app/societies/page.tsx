'use client';

import { Header } from '@/components/Header';
import { useState, useEffect } from 'react';
import { Instagram } from 'lucide-react';
import { api } from '@/lib/api';
import { Society } from '@/lib/types';

export default function SocietiesPage() {
  const [societies, setSocieties] = useState<Society[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSocieties = async () => {
      try {
        const data = await api.getSocieties();
        setSocieties(data);
      } catch (err) {
        setError('Failed to load societies');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchSocieties();
  }, []);

  return (
    <div className="min-h-screen bg-white">
      <Header />
      
      <main className="pt-24 pb-16 px-4">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              monitored societies
            </h1>
            <p className="text-lg text-gray-600">
              we track these {societies.length} UCD societies for free food announcements
            </p>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-12">
              <div className="inline-block w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
              <p className="text-gray-600 mt-4">loading societies...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="text-center py-12">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          {/* Societies List - Simple Design */}
          {!loading && !error && (
            <>
              <div className="space-y-3 mb-12">
                {societies.map((society) => (
                  <a
                    key={society.id}
                    href={`https://instagram.com/${society.instagram_handle}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-4 rounded-lg hover:bg-gray-50 transition-colors group"
                  >
                    <div className="flex items-center gap-3">
                      <Instagram className="w-5 h-5 text-gray-400 group-hover:text-primary transition-colors" />
                      <div>
                        <h3 className="font-semibold text-gray-900 group-hover:text-primary transition-colors">
                          {society.name}
                        </h3>
                        <p className="text-sm text-gray-500">
                          @{society.instagram_handle}
                        </p>
                      </div>
                    </div>
                    {society.is_active && (
                      <span className="text-xs font-medium text-green-600 bg-green-50 px-3 py-1 rounded-full">
                        active
                      </span>
                    )}
                  </a>
                ))}
              </div>

              {/* Stats */}
              <div className="bg-gray-50 rounded-xl p-8 text-center">
                <div className="text-4xl font-bold text-primary mb-2">
                  {societies.length}
                </div>
                <div className="text-gray-600">societies monitored 24/7</div>
              </div>
            </>
          )}

          {/* Missing Society CTA */}
          <div className="mt-12 text-center bg-primary/5 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-3">
              missing a society?
            </h2>
            <p className="text-gray-600 mb-6">
              let us know and we'll add them
            </p>
            <a
              href="mailto:hello@freefooducd.ie"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-primary text-white font-semibold hover:bg-primary-dark transition-all"
            >
              suggest a society
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}

// Made with Bob