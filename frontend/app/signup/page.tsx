'use client';

import { Header } from '@/components/Header';
import { useState, useEffect, Suspense } from 'react';
import { Mail, ArrowRight, Check, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useSearchParams } from 'next/navigation';

function SignupContent() {
  const searchParams = useSearchParams();
  const emailFromUrl = searchParams.get('email');
  
  const [step, setStep] = useState<'form' | 'verify' | 'success'>(emailFromUrl ? 'verify' : 'form');
  const [email, setEmail] = useState(emailFromUrl || '');
  const [verificationCode, setVerificationCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    if (emailFromUrl) {
      setEmail(emailFromUrl);
      setStep('verify');
    }
  }, [emailFromUrl]);

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
        setError('already signed up fatty');
      } else {
        setError(err instanceof Error ? err.message : 'something went wrong, try again');
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
                <span className="inline-block px-5 py-2 rounded-full bg-primary/10 text-primary text-sm font-bold mb-6 border-2 border-primary/20">
                  never miss free food again
                </span>
              </div>

              <div className="text-6xl mb-6">🍕</div>

              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-text mb-4">
                get started
              </h1>
              <p className="text-lg md:text-xl text-text-light mb-12">
                enter your email to receive instant notifications
              </p>

              <form onSubmit={handleSubmit} className="max-w-md mx-auto">
                {error && (
                  <div className="mb-6 p-4 rounded-2xl bg-danger/10 border-2 border-danger/20 flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-danger-dark flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-danger-dark font-bold text-left">{error}</p>
                  </div>
                )}

                <div className="mb-6">
                  <div className="relative">
                    <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                      <Mail className="w-5 h-5 text-text-lighter" />
                    </div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="your.email@ucd.ie"
                      className="w-full pl-12 pr-4 py-4 rounded-2xl border-2 border-gray-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 text-lg transition-all bg-white"
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full px-8 py-4 rounded-2xl bg-accent text-white text-lg font-bold hover:bg-accent-dark transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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
              </form>
            </div>
          )}

          {/* Step 2: Verification */}
          {step === 'verify' && (
            <div className="text-center">
              <div className="w-20 h-20 rounded-3xl bg-primary/10 flex items-center justify-center mx-auto mb-6 border-2 border-primary/20">
                <Mail className="w-10 h-10 text-primary" />
              </div>
              
              <h1 className="text-4xl md:text-5xl font-bold text-text mb-4">
                check your email 📬
              </h1>
              
              <p className="text-lg text-text-light mb-8">
                we sent a 6-digit code to<br />
                <span className="font-bold text-text">{email}</span>
              </p>

              <form onSubmit={handleVerify} className="max-w-md mx-auto">
                {error && (
                  <div className="mb-6 p-4 rounded-2xl bg-danger/10 border-2 border-danger/20 flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-danger-dark flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-danger-dark font-bold text-left">{error}</p>
                  </div>
                )}

                <div className="mb-6">
                  <input
                    type="text"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    maxLength={6}
                    className="w-full px-6 py-5 rounded-2xl border-2 border-gray-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 text-center text-3xl font-bold tracking-[0.5em] transition-all bg-white"
                    required
                  />
                  <p className="text-sm text-text-lighter mt-2 font-medium">
                    code expires in 10 minutes
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || verificationCode.length !== 6}
                  className="w-full px-8 py-4 rounded-2xl bg-accent text-white text-lg font-bold hover:bg-accent-dark transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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

                <Link
                  href="/"
                  className="mt-4 inline-block text-text-light hover:text-text font-bold transition-colors"
                >
                  ← use different email
                </Link>
              </form>
            </div>
          )}

          {/* Step 3: Success */}
          {step === 'success' && (
            <div className="text-center">
              <div className="w-24 h-24 rounded-3xl bg-accent/10 flex items-center justify-center mx-auto mb-6 border-2 border-accent/20">
                <Check className="w-12 h-12 text-accent-dark" />
              </div>
              
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-text mb-4">
                you're in! 🎉
              </h1>
              
              <p className="text-lg md:text-xl text-text-light mb-12">
                you'll now get instant email alerts about free food events
              </p>

              <div className="bg-gray-50 rounded-3xl p-8 mb-8 max-w-md mx-auto border-2 border-gray-100">
                <h3 className="text-xl font-bold text-text mb-6">what's next?</h3>
                <ul className="text-left space-y-4">
                  <li className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-white text-sm font-bold flex items-center justify-center mt-0.5">1</span>
                    <span className="text-text-light font-medium">we monitor UCD society Instagram accounts</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-white text-sm font-bold flex items-center justify-center mt-0.5">2</span>
                    <span className="text-text-light font-medium">when free food is posted, you get an instant email</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-white text-sm font-bold flex items-center justify-center mt-0.5">3</span>
                    <span className="text-text-light font-medium">never miss free food again!</span>
                  </li>
                </ul>
              </div>

              <Link
                href="/"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl text-primary hover:bg-primary/10 transition-all font-bold border-2 border-primary/20"
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

export default function SignupPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-white">
        <Header />
        <main className="pt-24 pb-16 px-4">
          <div className="max-w-2xl mx-auto text-center">
            <div className="inline-block w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
            <p className="text-text-light mt-4 font-semibold">loading...</p>
          </div>
        </main>
      </div>
    }>
      <SignupContent />
    </Suspense>
  );
}

// Made with Bob