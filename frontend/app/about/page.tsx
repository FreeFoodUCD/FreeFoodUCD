import { Header } from '@/components/Header';
import { Zap, Bell, Shield } from 'lucide-react';

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      
      <main className="pt-24 pb-16 px-4">
        <div className="max-w-3xl mx-auto">
          {/* Hero */}
          <div className="text-center mb-16">
            <div className="text-6xl md:text-7xl mb-6">🍕</div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-text mb-6">
              never miss free food again
            </h1>
            <p className="text-lg md:text-xl text-text-light font-medium">
              instant email alerts when UCD societies post about free food
            </p>
          </div>

          {/* How It Works */}
          <div className="mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-text mb-10 text-center">
              how it works
            </h2>
            <div className="space-y-5">
              <div className="flex gap-4 p-5 bg-gray-50 rounded-3xl border-2 border-gray-100">
                <div className="flex-shrink-0 w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center">
                  <span className="text-2xl font-bold text-primary">1</span>
                </div>
                <div>
                  <h3 className="text-lg md:text-xl font-bold text-text mb-1">sign up with your email</h3>
                  <p className="text-text-light font-medium">takes 30 seconds, no app needed</p>
                </div>
              </div>
              
              <div className="flex gap-4 p-5 bg-gray-50 rounded-3xl border-2 border-gray-100">
                <div className="flex-shrink-0 w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center">
                  <span className="text-2xl font-bold text-primary">2</span>
                </div>
                <div>
                  <h3 className="text-lg md:text-xl font-bold text-text mb-1">we monitor 22 societies</h3>
                  <p className="text-text-light font-medium">checking Instagram posts 24/7 for free food</p>
                </div>
              </div>
              
              <div className="flex gap-4 p-5 bg-gray-50 rounded-3xl border-2 border-gray-100">
                <div className="flex-shrink-0 w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center">
                  <span className="text-2xl font-bold text-primary">3</span>
                </div>
                <div>
                  <h3 className="text-lg md:text-xl font-bold text-text mb-1">get instant alerts</h3>
                  <p className="text-text-light font-medium">email notification within minutes of announcement</p>
                </div>
              </div>
            </div>
          </div>

          {/* The Story */}
          <div className="mb-16 bg-gray-50 rounded-3xl p-8 md:p-10 border-2 border-gray-100">
            <h2 className="text-3xl md:text-4xl font-bold text-text mb-6 text-center">
              why we built this
            </h2>
            <div className="space-y-4 text-text-light text-base md:text-lg leading-relaxed">
              <p className="font-medium">
                we kept missing free food because we didn't see the Instagram post in time.
              </p>
              <p className="font-medium">
                societies post about free pizza, but by the time we saw it, the food was gone.
              </p>
              <p className="font-medium">
                so we built this - an automated system that watches society Instagram accounts
                and sends instant email alerts when free food is available.
              </p>
              <p className="text-text font-bold text-lg md:text-xl">
                now no UCD student has to miss free pizza again 🍕
              </p>
            </div>
          </div>

          {/* CTA */}
          <div className="text-center bg-gray-50 rounded-3xl p-10 md:p-12 border-2 border-gray-200">
            <h2 className="text-3xl md:text-4xl font-bold text-text mb-4">
              ready to get started?
            </h2>
            <p className="text-lg md:text-xl text-text-light mb-8 font-medium">
              join students getting instant free food alerts
            </p>
            <a
              href="/"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl bg-accent text-white text-lg font-bold hover:bg-accent-dark transition-all shadow-md hover:shadow-lg"
            >
              sign up now
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}

// Made with Bob