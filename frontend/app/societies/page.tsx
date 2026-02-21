'use client';

import { Header } from '@/components/Header';
import { useState, useEffect } from 'react';
import { Instagram, CheckCircle, Clock } from 'lucide-react';
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
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              monitored societies
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              we track these UCD societies 24/7 for free food announcements
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

          {/* Societies Grid */}
          {!loading && !error && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
                {societies.map((society) => (
                  <div
                    key={society.id}
                    className="p-6 rounded-2xl border-2 border-gray-200 hover:border-primary hover:shadow-lg transition-all"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <h3 className="text-xl font-bold text-gray-900 mb-2">
                          {society.name}
                        </h3>
                        <a
                          href={`https://instagram.com/${society.instagram_handle}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-gray-600 hover:text-primary transition-colors"
                        >
                          <Instagram className="w-4 h-4" />
                          <span className="text-sm">@{society.instagram_handle}</span>
                        </a>
                      </div>
                      {society.is_active && (
                        <div className="flex items-center gap-1 text-green-600 text-sm">
                          <CheckCircle className="w-4 h-4" />
                          <span>active</span>
                        </div>
                      )}
                    </div>

                    <div className="space-y-2 text-sm text-gray-600">
                      {society.scrape_posts && (
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4" />
                          <span>monitoring posts</span>
                        </div>
                      )}
                      {society.scrape_stories && (
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4" />
                          <span>monitoring stories</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Stats */}
              <div className="bg-gray-50 rounded-2xl p-8 text-center">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                  <div>
                    <div className="text-4xl font-bold text-primary mb-2">
                      {societies.length}
                    </div>
                    <div className="text-gray-600">societies tracked</div>
                  </div>
                  <div>
                    <div className="text-4xl font-bold text-primary mb-2">
                      {societies.filter(s => s.scrape_stories).length}
                    </div>
                    <div className="text-gray-600">story monitoring</div>
                  </div>
                  <div>
                    <div className="text-4xl font-bold text-primary mb-2">
                      {societies.filter(s => s.is_active).length}
                    </div>
                    <div className="text-gray-600">currently active</div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Missing Society CTA */}
          <div className="mt-12 text-center bg-primary/5 rounded-2xl p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              missing a society?
            </h2>
            <p className="text-gray-600 mb-6">
              let us know and we'll add them to our monitoring list
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