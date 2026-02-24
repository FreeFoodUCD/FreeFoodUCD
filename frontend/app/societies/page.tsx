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
            <div className="text-6xl mb-6">👥</div>
            <h1 className="text-4xl md:text-5xl font-bold text-text mb-4">
              monitored societies
            </h1>
            <p className="text-lg md:text-xl text-text-light font-medium">
              we track these {societies.length} UCD societies for free food announcements
            </p>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-16 bg-gray-50 rounded-3xl border-2 border-gray-100">
              <div className="inline-block w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
              <p className="text-text-light mt-4 font-semibold">loading societies...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="text-center py-16 bg-gray-50 rounded-3xl border-2 border-gray-100">
              <p className="text-danger-dark font-bold">{error}</p>
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
                    className="flex items-center justify-between p-5 bg-gray-50 rounded-2xl hover:shadow-lg transition-all group border-2 border-gray-100 hover:border-primary/30"
                  >
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-primary/10 rounded-xl group-hover:bg-primary/20 transition-all">
                        <Instagram className="w-5 h-5 text-primary" />
                      </div>
                      <div>
                        <h3 className="font-bold text-text group-hover:text-primary transition-colors">
                          {society.name}
                        </h3>
                        <p className="text-sm text-text-lighter font-medium">
                          @{society.instagram_handle}
                        </p>
                      </div>
                    </div>
                    {society.is_active && (
                      <span className="text-xs font-bold text-success-dark bg-success/10 px-3 py-1.5 rounded-full border-2 border-success/20">
                        active
                      </span>
                    )}
                  </a>
                ))}
              </div>

              {/* Stats */}
              <div className="bg-gray-50 rounded-3xl p-8 md:p-10 text-center border-2 border-gray-200">
                <div className="text-5xl md:text-6xl font-bold text-primary mb-3">
                  {societies.length}
                </div>
                <div className="text-lg text-text-light font-semibold">societies monitored 24/7</div>
              </div>
            </>
          )}

          {/* Missing Society CTA */}
          <div className="mt-12 text-center bg-gray-50 rounded-3xl p-8 md:p-10 border-2 border-gray-100">
            <h2 className="text-2xl md:text-3xl font-bold text-text mb-3">
              missing a society?
            </h2>
            <p className="text-text-light mb-6 font-medium">
              let us know and we'll add them
            </p>
            <a
              href="mailto:freefooducd@outlook.com"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-accent text-white font-bold hover:bg-accent-dark transition-all shadow-md hover:shadow-lg"
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