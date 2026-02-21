'use client';

import { Header } from '@/components/Header';
import { useState } from 'react';
import { Mail, ArrowRight, Check, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';

export default function SignupPage() {
  const [step, setStep] = useState<'form' | 'verify' | 'success'>('form');
  const [email, setEmail] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await api.signup({ email });
      setUserId(response.id);
      setStep('verify');
    } catch (err: any) {
      if (err.message === 'already_signed_up' || err.message.includes('already exists')) {
        setError('You\'re already signed up! Check your email for notifications.');
      } else {
        setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await api.verify({ email, code: verificationCode });
      setStep('success');
    } catch (err: any) {
      setError(err instanceof Error ? err.message : 'Invalid code. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <Header />
      
      <main className="pt-24 pb-16 px-4">
        <div className="max-w-2xl mx-auto">
          
          {/* Step 1: Email Form */}
          {step === 'form' && (
            <div className="text-center">
              <div className="mb-8">
                <span className="inline-block px-4 py-2 rounded-full bg-blue-50 text-primary text-sm font-semibold mb-6">
                  never miss free food again
                </span>
              </div>

              <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-4">
                get started 🍕
              </h1>
              <p className="text-xl text-gray-600 mb-12">
                enter your email to receive instant notifications
              </p>

              <form onSubmit={handleSubmit} className="max-w-md mx-auto">
                {error && (
                  <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-800 font-medium">{error}</p>
                  </div>
                )}

                <div className="mb-6">
                  <div className="relative">
                    <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                      <Mail className="w-5 h-5 text-gray-400" />
                    </div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="your.email@ucd.ie"
                      className="w-full pl-12 pr-4 py-4 rounded-xl border-2 border-gray-200 focus:border-primary focus:outline-none text-lg transition-colors"
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full px-8 py-4 rounded-xl bg-primary text-white text-lg font-semibold hover:bg-primary-dark transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      sending...
                    </>
                  ) : (
                    <>
                      continue
                      <ArrowRight className="w-5 h-5" />
                    </>
                  )}
                </button>

                <p className="text-sm text-gray-500 mt-4">
                  by signing up, you agree to receive email notifications
                </p>
              </form>
            </div>
          )}

          {/* Step 2: Verification */}
          {step === 'verify' && (
            <div className="text-center">
              <div className="w-20 h-20 rounded-full bg-blue-50 flex items-center justify-center mx-auto mb-6">
                <Mail className="w-10 h-10 text-primary" />
              </div>
              
              <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                check your email 📬
              </h1>
              
              <p className="text-lg text-gray-600 mb-8">
                we sent a 6-digit code to<br />
                <span className="font-semibold text-gray-900">{email}</span>
              </p>

              <form onSubmit={handleVerify} className="max-w-md mx-auto">
                {error && (
                  <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-800 font-medium">{error}</p>
                  </div>
                )}

                <div className="mb-6">
                  <input
                    type="text"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    maxLength={6}
                    className="w-full px-6 py-5 rounded-xl border-2 border-gray-200 focus:border-primary focus:outline-none text-center text-3xl font-bold tracking-[0.5em] transition-colors"
                    required
                  />
                  <p className="text-sm text-gray-500 mt-2">
                    code expires in 10 minutes
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || verificationCode.length !== 6}
                  className="w-full px-8 py-4 rounded-xl bg-primary text-white text-lg font-semibold hover:bg-primary-dark transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      verifying...
                    </>
                  ) : (
                    <>
                      verify & complete
                      <Check className="w-5 h-5" />
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setStep('form')}
                  className="mt-4 text-gray-600 hover:text-gray-900 font-medium transition-colors"
                >
                  ← use different email
                </button>
              </form>
            </div>
          )}

          {/* Step 3: Success */}
          {step === 'success' && (
            <div className="text-center">
              <div className="w-24 h-24 rounded-full bg-green-50 flex items-center justify-center mx-auto mb-6">
                <Check className="w-12 h-12 text-green-600" />
              </div>
              
              <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-4">
                you're in! 🎉
              </h1>
              
              <p className="text-xl text-gray-600 mb-12">
                you'll now get instant email alerts about free food events
              </p>

              <div className="bg-gray-50 rounded-2xl p-8 mb-8 max-w-md mx-auto">
                <h3 className="text-xl font-bold text-gray-900 mb-6">what's next?</h3>
                <ul className="text-left space-y-4">
                  <li className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-white text-sm font-bold flex items-center justify-center mt-0.5">1</span>
                    <span className="text-gray-700">we monitor UCD society Instagram accounts</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-white text-sm font-bold flex items-center justify-center mt-0.5">2</span>
                    <span className="text-gray-700">when free food is posted, you get an instant email</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-white text-sm font-bold flex items-center justify-center mt-0.5">3</span>
                    <span className="text-gray-700">never miss free food again!</span>
                  </li>
                </ul>
              </div>

              <Link
                href="/"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-primary hover:bg-blue-50 transition-colors font-semibold"
              >
                ← back to home
              </Link>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

// Made with Bob