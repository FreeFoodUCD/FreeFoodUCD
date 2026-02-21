'use client';

import { Header } from '@/components/Header';
import { useState } from 'react';
import { Mail, ArrowRight, Check, AlertCircle, Sparkles } from 'lucide-react';
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
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50">
      <Header />
      
      <main className="pt-24 pb-16 px-4">
        <div className="max-w-2xl mx-auto">
          
          {/* Step 1: Email Form */}
          {step === 'form' && (
            <div className="text-center">
              {/* Decorative Elements */}
              <div className="relative mb-8">
                <div className="absolute -top-4 -left-4 w-24 h-24 bg-yellow-200 rounded-full opacity-50 blur-2xl"></div>
                <div className="absolute -top-4 -right-4 w-32 h-32 bg-purple-200 rounded-full opacity-50 blur-2xl"></div>
                
                <div className="relative">
                  <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-100 text-purple-700 text-sm font-semibold mb-6">
                    <Sparkles className="w-4 h-4" />
                    never miss free food again
                  </div>
                </div>
              </div>

              <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-4">
                get started 🍕
              </h1>
              <p className="text-xl text-gray-600 mb-12">
                enter your email to receive instant notifications
              </p>

              <form onSubmit={handleSubmit} className="max-w-md mx-auto">
                {/* Error Message */}
                {error && (
                  <div className="mb-6 p-4 rounded-2xl bg-red-50 border-2 border-red-200 flex items-start gap-3 animate-shake">
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-800 font-medium">{error}</p>
                  </div>
                )}

                {/* Email Input with Cartoon Style */}
                <div className="mb-6 relative">
                  <div className="absolute -inset-1 bg-gradient-to-r from-purple-400 to-blue-400 rounded-2xl opacity-20 blur"></div>
                  <div className="relative bg-white rounded-2xl border-3 border-gray-900 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] transition-all">
                    <div className="flex items-center gap-3 p-4">
                      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center flex-shrink-0">
                        <Mail className="w-6 h-6 text-white" />
                      </div>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="your.email@ucd.ie"
                        className="flex-1 text-lg font-medium text-gray-900 placeholder-gray-400 focus:outline-none bg-transparent"
                        required
                      />
                    </div>
                  </div>
                </div>

                {/* Submit Button with Cartoon Style */}
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full px-8 py-5 rounded-2xl bg-gradient-to-r from-purple-500 to-blue-500 text-white text-lg font-bold border-3 border-gray-900 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-x-0 disabled:hover:translate-y-0 flex items-center justify-center gap-3"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-5 h-5 border-3 border-white border-t-transparent rounded-full animate-spin"></div>
                      sending magic link...
                    </>
                  ) : (
                    <>
                      let's go!
                      <ArrowRight className="w-6 h-6" />
                    </>
                  )}
                </button>

                <p className="text-sm text-gray-500 mt-4">
                  by signing up, you agree to receive email notifications about free food events
                </p>
              </form>
            </div>
          )}

          {/* Step 2: Verification */}
          {step === 'verify' && (
            <div className="text-center">
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center mx-auto mb-6 border-3 border-gray-900 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                <Mail className="w-12 h-12 text-white" />
              </div>
              
              <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                check your email! 📬
              </h1>
              
              <p className="text-lg text-gray-600 mb-8">
                we sent a 6-digit code to<br />
                <span className="font-semibold text-gray-900">{email}</span>
              </p>

              <form onSubmit={handleVerify} className="max-w-md mx-auto">
                {error && (
                  <div className="mb-6 p-4 rounded-2xl bg-red-50 border-2 border-red-200 flex items-start gap-3">
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
                    className="w-full px-6 py-5 rounded-2xl border-3 border-gray-900 text-center text-3xl font-bold tracking-[0.5em] focus:outline-none focus:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all"
                    required
                  />
                  <p className="text-sm text-gray-500 mt-2">
                    code expires in 10 minutes
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || verificationCode.length !== 6}
                  className="w-full px-8 py-5 rounded-2xl bg-gradient-to-r from-purple-500 to-blue-500 text-white text-lg font-bold border-3 border-gray-900 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-x-0 disabled:hover:translate-y-0 flex items-center justify-center gap-3"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-5 h-5 border-3 border-white border-t-transparent rounded-full animate-spin"></div>
                      verifying...
                    </>
                  ) : (
                    <>
                      verify & complete
                      <Check className="w-6 h-6" />
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setStep('form')}
                  className="mt-4 text-gray-600 hover:text-gray-900 font-medium"
                >
                  ← use different email
                </button>
              </form>
            </div>
          )}

          {/* Step 3: Success */}
          {step === 'success' && (
            <div className="text-center">
              <div className="relative mb-8">
                <div className="absolute inset-0 bg-gradient-to-r from-green-200 to-blue-200 rounded-full opacity-50 blur-3xl animate-pulse"></div>
                <div className="relative w-32 h-32 rounded-full bg-gradient-to-br from-green-400 to-blue-500 flex items-center justify-center mx-auto border-4 border-gray-900 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
                  <Check className="w-16 h-16 text-white" strokeWidth={3} />
                </div>
              </div>
              
              <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-4">
                you're in! 🎉
              </h1>
              
              <p className="text-xl text-gray-600 mb-12">
                you'll now get instant email alerts about free food events
              </p>

              <div className="bg-white rounded-3xl p-8 mb-8 max-w-md mx-auto border-3 border-gray-900 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
                <h3 className="text-2xl font-bold text-gray-900 mb-6">what's next?</h3>
                <ul className="text-left space-y-4">
                  <li className="flex items-start gap-4">
                    <span className="flex-shrink-0 w-8 h-8 rounded-full bg-purple-500 text-white font-bold flex items-center justify-center border-2 border-gray-900">1</span>
                    <span className="text-gray-700 font-medium pt-1">we monitor UCD society Instagram accounts</span>
                  </li>
                  <li className="flex items-start gap-4">
                    <span className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 text-white font-bold flex items-center justify-center border-2 border-gray-900">2</span>
                    <span className="text-gray-700 font-medium pt-1">when free food is posted, you get an instant email</span>
                  </li>
                  <li className="flex items-start gap-4">
                    <span className="flex-shrink-0 w-8 h-8 rounded-full bg-green-500 text-white font-bold flex items-center justify-center border-2 border-gray-900">3</span>
                    <span className="text-gray-700 font-medium pt-1">never miss free food again!</span>
                  </li>
                </ul>
              </div>

              <Link
                href="/"
                className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl bg-gray-900 text-white font-bold border-3 border-gray-900 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all"
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