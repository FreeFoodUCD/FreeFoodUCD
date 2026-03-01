import Link from 'next/link';
import Image from 'next/image';

export function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white border-b-2 border-gray-100">
      <nav className="max-w-5xl mx-auto px-4 h-16 md:h-20 flex items-center justify-center" aria-label="Main navigation">
        <Link href="/" className="flex items-center gap-2 md:gap-3 group shrink-0" aria-label="FreeFood UCD — home">
          <div className="relative w-9 h-9 md:w-11 md:h-11 transition-transform group-hover:scale-110">
            <Image
              src="/FreeFoodUCDLogo_nobg.png"
              alt=""
              fill
              className="object-contain"
              priority
            />
          </div>
          <span className="text-lg md:text-xl font-bold text-text">
            FreeFood <span className="text-primary">UCD</span>
          </span>
        </Link>
      </nav>
    </header>
  );
}

// Made with Bob
