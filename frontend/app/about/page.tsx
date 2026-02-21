import { Header } from '@/components/Header';
import { Users, Bell, Zap, Shield } from 'lucide-react';

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      
      <main className="pt-24 pb-16 px-4">
        <div className="max-w-4xl mx-auto">
          {/* Hero Section */}
          <div className="text-center mb-16">
            <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
              never miss free food again
            </h1>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              FreeFoodUCD helps UCD students discover free food events from societies across campus in real-time.
            </p>
          </div>

          {/* How It Works */}
          <div className="mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
              how it works
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold text-primary">1</span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">sign up</h3>
                <p className="text-gray-600">
                  choose WhatsApp or email notifications
                </p>
              </div>
              
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold text-primary">2</span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">we monitor</h3>
                <p className="text-gray-600">
                  our system tracks society Instagram posts & stories 24/7
                </p>
              </div>
              
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold text-primary">3</span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">get notified</h3>
                <p className="text-gray-600">
                  instant alerts when free food is available
                </p>
              </div>
            </div>
          </div>

          {/* Features */}
          <div className="mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
              why students love us
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-6 rounded-2xl border-2 border-gray-200">
                <Zap className="w-8 h-8 text-primary mb-4" />
                <h3 className="text-xl font-bold text-gray-900 mb-2">instant alerts</h3>
                <p className="text-gray-600">
                  get notified within minutes of free food being announced
                </p>
              </div>
              
              <div className="p-6 rounded-2xl border-2 border-gray-200">
                <Bell className="w-8 h-8 text-primary mb-4" />
                <h3 className="text-xl font-bold text-gray-900 mb-2">smart filtering</h3>
                <p className="text-gray-600">
                  only get alerts for events on UCD campus with confirmed free food
                </p>
              </div>
              
              <div className="p-6 rounded-2xl border-2 border-gray-200">
                <Users className="w-8 h-8 text-primary mb-4" />
                <h3 className="text-xl font-bold text-gray-900 mb-2">all societies</h3>
                <p className="text-gray-600">
                  we monitor 20+ UCD societies so you don't have to
                </p>
              </div>
              
              <div className="p-6 rounded-2xl border-2 border-gray-200">
                <Shield className="w-8 h-8 text-primary mb-4" />
                <h3 className="text-xl font-bold text-gray-900 mb-2">privacy first</h3>
                <p className="text-gray-600">
                  your data is secure and we never spam you
                </p>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="bg-gray-50 rounded-2xl p-8 mb-16">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
              <div>
                <div className="text-4xl font-bold text-primary mb-2">20+</div>
                <div className="text-gray-600">societies monitored</div>
              </div>
              <div>
                <div className="text-4xl font-bold text-primary mb-2">24/7</div>
                <div className="text-gray-600">real-time monitoring</div>
              </div>
              <div>
                <div className="text-4xl font-bold text-primary mb-2">{'<5min'}</div>
                <div className="text-gray-600">average alert time</div>
              </div>
            </div>
          </div>

          {/* The Story */}
          <div className="mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-6 text-center">
              our story
            </h2>
            <div className="prose prose-lg max-w-none text-gray-600">
              <p className="mb-4">
                FreeFoodUCD was born from a simple frustration: constantly missing out on free food events 
                because we didn't see the Instagram story in time.
              </p>
              <p className="mb-4">
                As UCD students, we noticed that societies often announce free food on Instagram stories 
                that disappear after 24 hours. By the time we saw them, the food was usually gone.
              </p>
              <p>
                So we built FreeFoodUCD - an automated system that monitors society Instagram accounts 
                and sends instant notifications when free food is available. Now, no student has to miss 
                out on free pizza ever again! 🍕
              </p>
            </div>
          </div>

          {/* CTA */}
          <div className="text-center bg-primary/5 rounded-2xl p-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              ready to never miss free food?
            </h2>
            <p className="text-lg text-gray-600 mb-8">
              join hundreds of UCD students getting instant alerts
            </p>
            <a
              href="/signup"
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