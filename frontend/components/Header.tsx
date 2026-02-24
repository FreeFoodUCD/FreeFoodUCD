'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useState } from 'react';

export function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white border-b-2 border-gray-100">
      <div className="max-w-7xl mx-auto px-4 h-16 md:h-20 flex items-center justify-between relative">

        {/* Logo — always left */}
        <Link href="/" className="flex items-center gap-2 md:gap-3 group shrink-0">
          <div className="relative w-9 h-9 md:w-11 md:h-11 transition-transform group-hover:scale-110">
            <Image
              src="/FreeFoodUCDLogo_nobg.png"
              alt="FreeFood UCD Logo"
              fill
              className="object-contain"
              priority
            />
          </div>
          <h1 className="text-lg md:text-xl font-bold text-text">
            FreeFood <span className="text-primary">UCD</span>
          </h1>
        </Link>

        {/* Desktop Nav — absolute center */}
        <nav className="hidden md:flex items-center gap-1 absolute left-1/2 -translate-x-1/2">
          <Link href="/" className="px-4 py-2 text-sm font-semibold text-text-light hover:text-primary hover:bg-primary/5 rounded-xl transition-all">
            Events
          </Link>
          <Link href="/societies" className="px-4 py-2 text-sm font-semibold text-text-light hover:text-primary hover:bg-primary/5 rounded-xl transition-all">
            Societies
          </Link>
          <Link href="/about" className="px-4 py-2 text-sm font-semibold text-text-light hover:text-primary hover:bg-primary/5 rounded-xl transition-all">
            About
          </Link>
        </nav>

        {/* Hamburger — mobile only */}
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className="md:hidden p-2 text-text hover:bg-gray-50 rounded-xl transition-all"
          aria-label="Toggle menu"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {isMenuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile Menu */}
      {isMenuOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white">
          <nav className="px-4 py-4 space-y-1">
            <Link href="/" className="block px-4 py-3 text-base font-semibold text-text hover:bg-primary/5 hover:text-primary rounded-xl transition-all" onClick={() => setIsMenuOpen(false)}>
              Events
            </Link>
            <Link href="/societies" className="block px-4 py-3 text-base font-semibold text-text hover:bg-primary/5 hover:text-primary rounded-xl transition-all" onClick={() => setIsMenuOpen(false)}>
              Societies
            </Link>
            <Link href="/about" className="block px-4 py-3 text-base font-semibold text-text hover:bg-primary/5 hover:text-primary rounded-xl transition-all" onClick={() => setIsMenuOpen(false)}>
              About
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}

// Made with Bob
