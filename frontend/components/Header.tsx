'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useState } from 'react';

export function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-primary shadow-md">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="relative w-10 h-10 transition-transform group-hover:scale-110">
            <Image
              src="/FreeFoodUCDLogo.jpeg"
              alt="FreeFood UCD Logo"
              fill
              className="object-contain"
              priority
            />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">
              FreeFood <span className="text-white/90">UCD</span>
            </h1>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-6">
          <Link
            href="/"
            className="text-sm font-medium text-white/90 hover:text-white transition-colors"
          >
            Events
          </Link>
          <Link
            href="/societies"
            className="text-sm font-medium text-white/90 hover:text-white transition-colors"
          >
            Societies
          </Link>
          <Link
            href="/about"
            className="text-sm font-medium text-white/90 hover:text-white transition-colors"
          >
            About
          </Link>
        </nav>

        {/* Mobile Menu Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="md:hidden p-2 text-white hover:text-white/80"
            aria-label="Toggle menu"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {isMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMenuOpen && (
        <div className="md:hidden border-t border-white/20 bg-primary-dark">
          <nav className="px-4 py-4 space-y-3">
            <Link
              href="/"
              className="block px-3 py-2 text-base font-medium text-white hover:bg-white/10 rounded-lg"
              onClick={() => setIsMenuOpen(false)}
            >
              Events
            </Link>
            <Link
              href="/societies"
              className="block px-3 py-2 text-base font-medium text-white hover:bg-white/10 rounded-lg"
              onClick={() => setIsMenuOpen(false)}
            >
              Societies
            </Link>
            <Link
              href="/about"
              className="block px-3 py-2 text-base font-medium text-white hover:bg-white/10 rounded-lg"
              onClick={() => setIsMenuOpen(false)}
            >
              About
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}

// Made with Bob
