'use client';

import { Header } from '@/components/Header';
import { useState } from 'react';
import { Smartphone, Mail, ArrowRight, Check, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';

type NotificationType = 'whatsapp' | 'email' | null;

export default function SignupPage() {
  const [step, setStep] = useState<'choose' | 'form' | 'success'>('choose');
  const [notificationType, setNotificationType] = useState<NotificationType>(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);

  const handleChooseType = (type: NotificationType) => {
    setNotificationType(type);
    setStep('form');
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      // Prepare data for API
      const signupData = notificationType === 'whatsapp'
        ? { phone_number: `+353${phoneNumber.replace(/\s/g, '')}` }
        : { email };

      // Call API
      const response = await api.signup(signupData);
      
      // Store user ID for future use
      setUserId(response.id);
      
      // Move to success step
      setStep('success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <Header />
      
      <main className="pt-24 pb-16 px-4">
        <div className="max-w-2xl mx-auto">
          
          {/* Step 1: Choose Notification Type */}
          {step === 'choose' && (
            <div className="text-center">
              <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                how do you want alerts?
              </h1>
              <p className="text-lg text-gray-600 mb-12">
                pick your preferred notification method
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-xl mx-auto">
                {/* WhatsApp Option */}
                <button
                  onClick={() => handleChooseType('whatsapp')}
                  className="group p-8 rounded-2xl border-2 border-gray-200 hover:border-primary hover:bg-primary/5 transition-all text-center"
                >
                  <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                    <Smartphone className="w-8 h-8 text-green-600" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">WhatsApp</h3>
                  <p className="text-sm text-gray-600">
                    instant notifications on your phone
                  </p>
                </button>

                {/* Email Option */}
                <button
                  onClick={() => handleChooseType('email')}
                  className="group p-8 rounded-2xl border-2 border-gray-200 hover:border-primary hover:bg-primary/5 transition-all text-center"
                >
                  <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                    <Mail className="w-8 h-8 text-blue-600" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">Email</h3>
                  <p className="text-sm text-gray-600">
                    instant notifications via email
                  </p>
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Form */}
          {step === 'form' && (
            <div>
              <button
                onClick={() => setStep('choose')}
                className="text-gray-600 hover:text-gray-900 mb-6 flex items-center gap-2"
              >
                ← back
              </button>

              <div className="text-center mb-8">
                <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                  {notificationType === 'whatsapp' ? 'enter your number' : 'enter your email'}
                </h1>
                <p className="text-lg text-gray-600">
                  {notificationType === 'whatsapp' 
                    ? "we'll send you a verification code"
                    : "we'll send you a confirmation link"}
                </p>
              </div>

              <form onSubmit={handleSubmit} className="max-w-md mx-auto">
                {/* Error Message */}
                {error && (
                  <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-800">{error}</p>
                  </div>
                )}

                {notificationType === 'whatsapp' ? (
                  <div className="mb-6">
                    <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-2">
                      phone number
                    </label>
                    <div className="flex gap-2">
                      <div className="w-20 px-4 py-3 rounded-lg border-2 border-gray-200 bg-gray-50 text-center font-semibold text-gray-700">
                        +353
                      </div>
                      <input
                        type="tel"
                        id="phone"
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                        placeholder="85 123 4567"
                        className="flex-1 px-4 py-3 rounded-lg border-2 border-gray-200 focus:border-primary focus:outline-none text-lg"
                        required
                      />
                    </div>
                    <p className="text-sm text-gray-500 mt-2">
                      standard rates may apply
                    </p>
                  </div>
                ) : (
                  <div className="mb-6">
                    <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                      email address
                    </label>
                    <input
                      type="email"
                      id="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="your.email@ucd.ie"
                      className="w-full px-4 py-3 rounded-lg border-2 border-gray-200 focus:border-primary focus:outline-none text-lg"
                      required
                    />
                  </div>
                )}

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
              </form>
            </div>
          )}

          {/* Step 3: Success */}
          {step === 'success' && (
            <div className="text-center">
              <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-6">
                <Check className="w-10 h-10 text-green-600" />
              </div>
              
              <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                you're all set! 🎉
              </h1>
              
              <p className="text-lg text-gray-600 mb-8">
                {notificationType === 'whatsapp' 
                  ? `we sent a verification code to +353 ${phoneNumber}`
                  : `check your inbox at ${email}`}
              </p>

              <div className="bg-gray-50 rounded-2xl p-6 mb-8 max-w-md mx-auto">
                <h3 className="font-semibold text-gray-900 mb-3">what happens next?</h3>
                <ul className="text-left space-y-2 text-gray-600">
                  <li className="flex items-start gap-2">
                    <span className="text-primary font-bold">1.</span>
                    <span>{notificationType === 'whatsapp' ? 'verify your number' : 'confirm your email'}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary font-bold">2.</span>
                    <span>get instant alerts when free food drops</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary font-bold">3.</span>
                    <span>never miss out again</span>
                  </li>
                </ul>
              </div>

              <Link
                href="/"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-lg text-primary hover:bg-primary/5 transition-colors font-semibold"
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