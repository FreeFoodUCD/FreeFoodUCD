import { Header } from '@/components/Header';

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />

      <main className="pt-24 pb-16 px-4">
        <div className="max-w-2xl mx-auto text-center">

          {/* Hero */}
          <div className="mb-12">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-text mb-5">
              never miss free food again
            </h1>
            <p className="text-lg md:text-xl text-text-light font-medium leading-relaxed">
              we watch UCD society instagrams so you don't have to.<br />
              free food gets announced → you get an email. that's it.
            </p>
          </div>

          {/* Story */}
          <div className="mb-12 bg-gray-50 rounded-3xl p-8 border-2 border-gray-100 text-left">
            <p className="text-text-light font-medium text-base md:text-lg leading-relaxed">
              didn't wanna miss free food around campus, so made this myself.{' '}
              add me on linkedin:{' '}
              <a
                href="https://www.linkedin.com/in/adityasinha04/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline hover:text-primary-dark"
              >
                linkedin.com/in/adityasinha04
              </a>
              , feedback welcome :)
            </p>
          </div>

          {/* CTA */}
          <a
            href="/"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl bg-accent text-white text-lg font-bold hover:bg-accent-dark transition-all shadow-md hover:shadow-lg"
          >
            get free food alerts →
          </a>

        </div>
      </main>
    </div>
  );
}

// Made with Bob
