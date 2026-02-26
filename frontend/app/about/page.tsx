import { Header } from '@/components/Header';

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />

      <main className="pt-24 pb-16 px-4">
        <div className="max-w-2xl mx-auto text-center">

          {/* Hero */}
          <div className="mb-10">
            <h1 className="text-4xl md:text-5xl font-bold text-text mb-4">
              about
            </h1>
            <p className="text-lg text-text-light font-medium leading-relaxed">
              we watch UCD society instagrams and email you when free food is happening.
            </p>
          </div>

          {/* Story */}
          <div className="mb-10 text-left">
            <p className="text-text-light font-medium text-base leading-relaxed">
              made this so i wouldn't miss free food around campus.{' '}
              <a
                href="https://www.linkedin.com/in/adityasinha04/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline hover:text-primary-dark"
              >
                linkedin
              </a>{' '}
              if you want to say hi or give feedback :)
            </p>
          </div>

          {/* CTA */}
          <a
            href="/"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl bg-accent text-white text-lg font-bold hover:bg-accent-dark transition-all shadow-md hover:shadow-lg"
          >
            join the waitlist →
          </a>

        </div>
      </main>
    </div>
  );
}

// Made with Bob
