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
            <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
              never miss free food again
            </h1>
            <p className="text-xl text-gray-600">
              instant email alerts when UCD societies post about free food
            </p>
          </div>

          {/* How It Works */}
          <div className="mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
              how it works
            </h2>
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <span className="text-xl font-bold text-primary">1</span>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-1">sign up with your email</h3>
                  <p className="text-gray-600">takes 30 seconds, no app needed</p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <span className="text-xl font-bold text-primary">2</span>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-1">we monitor 22 societies</h3>
                  <p className="text-gray-600">checking Instagram posts 24/7 for free food</p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <span className="text-xl font-bold text-primary">3</span>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-1">get instant alerts</h3>
                  <p className="text-gray-600">email notification within minutes of announcement</p>
                </div>
              </div>
            </div>
          </div>

          {/* Features */}
          <div className="mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
              why it's great
            </h2>
            <div className="space-y-6">
              <div className="flex gap-4">
                <Zap className="w-8 h-8 text-primary flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-1">instant alerts</h3>
                  <p className="text-gray-600">
                    get notified within minutes, not hours
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <Bell className="w-8 h-8 text-primary flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-1">smart filtering</h3>
                  <p className="text-gray-600">
                    only UCD campus events with confirmed free food
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <Shield className="w-8 h-8 text-primary flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-1">privacy first</h3>
                  <p className="text-gray-600">
                    no spam, unsubscribe anytime, your data stays private
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* The Story */}
          <div className="mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-6 text-center">
              why we built this
            </h2>
            <div className="prose prose-lg max-w-none text-gray-600 space-y-4">
              <p>
                we kept missing free food because we didn't see the Instagram post in time.
              </p>
              <p>
                societies post about free pizza, but by the time we saw it, the food was gone.
              </p>
              <p>
                so we built this - an automated system that watches society Instagram accounts 
                and sends instant email alerts when free food is available.
              </p>
              <p className="text-gray-900 font-semibold">
                now no UCD student has to miss free pizza again 🍕
              </p>
            </div>
          </div>

          {/* CTA */}
          <div className="text-center bg-primary/5 rounded-2xl p-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              ready to get started?
            </h2>
            <p className="text-lg text-gray-600 mb-8">
              join students getting instant free food alerts
            </p>
            <a
              href="/"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-primary text-white text-lg font-semibold hover:bg-primary-dark transition-all shadow-lg hover:shadow-xl"
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