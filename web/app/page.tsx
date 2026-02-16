'use client';

import React, { useEffect, useRef } from 'react';
import { BotDemo } from './components/home/BotDemo';
import { Generator } from './components/home/Generator';

export default function Home() {
  const trackRef = useRef<HTMLDivElement>(null);
  const progressBarRef = useRef<HTMLDivElement>(null);
  const workSectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    // Horizontal Scroll Logic
    const track = trackRef.current;
    const progressBar = progressBarRef.current;
    const workSection = workSectionRef.current;

    if (!track || !progressBar || !workSection) return;

    let currentScroll = 0;
    let targetScroll = 0;
    let currentProgress = 0;
    let targetProgress = 0;
    const ease = 0.08;

    const animate = () => {
      currentScroll += (targetScroll - currentScroll) * ease;
      currentProgress += (targetProgress - currentProgress) * ease;
      track.style.transform = `translateX(${currentScroll}px)`;
      progressBar.style.width = `${currentProgress * 100}%`;
      requestAnimationFrame(animate);
    };

    const handleScroll = () => {
      const workRect = workSection.getBoundingClientRect();
      if (workRect.top <= 0 && workRect.bottom >= 0) {
        const windowHeight = window.innerHeight;
        const scrollableHeight = workSection.offsetHeight - windowHeight;
        const workScrolled = -workRect.top;
        const percentage = Math.min(Math.max(workScrolled / scrollableHeight, 0), 1);
        targetScroll = -(track.scrollWidth - window.innerWidth) * percentage;
        targetProgress = percentage;
      }
    };

    window.addEventListener('scroll', handleScroll);
    animate();

    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  const scrollTo = (id: string) => {
    document.querySelector(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="bg-[#000000] text-[#fcfbf9] overflow-x-hidden">
      {/* Navigation */}
      <nav className="fixed flex md:px-12 md:py-8 z-50 text-white w-full pt-6 pr-6 pb-6 pl-6 top-0 left-0 items-center justify-between">
        <button onClick={() => scrollTo('#hero')} className="lowercase hover:opacity-70 transition-opacity cursor-pointer text-base font-semibold tracking-tighter uppercase font-geist">
          transcriptflow
        </button>
        <div className="flex gap-10 text-[10px] font-medium tracking-widest lowercase text-neutral-400">
          <button onClick={() => scrollTo('#features')} className="hover:text-white transition-colors cursor-pointer">features</button>
          <button onClick={() => scrollTo('#generator')} className="hover:text-white transition-colors cursor-pointer">try it</button>
          <button onClick={() => scrollTo('#studio')} className="hover:text-white transition-colors cursor-pointer">method</button>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="flex flex-col md:px-12 w-full h-screen pr-6 pl-6 relative" id="hero">
        {/* Colorful Gradient Orbs */}
        <div className="absolute top-0 right-0 w-[40vw] h-[40vw] bg-gradient-to-br from-cyan-500/20 via-purple-500/20 to-pink-500/20 rounded-full blur-[120px] -translate-y-1/4 translate-x-1/4 -z-20 animate-pulse" />
        <div className="absolute bottom-0 left-0 w-[35vw] h-[35vw] bg-gradient-to-tr from-purple-500/15 via-pink-500/15 to-cyan-500/15 rounded-full blur-[100px] translate-y-1/4 -translate-x-1/4 -z-20 animate-pulse" style={{ animationDelay: '1s' }} />

        <div className="flex-grow" />

        <div className="flex flex-col md:flex-row md:pb-20 w-full border-neutral-900 border-b pb-12 items-end justify-between">
          <div className="reveal-text md:mb-0 md:w-auto w-full mb-10">
            <p className="md:text-base leading-relaxed lowercase text-sm font-normal text-neutral-300 tracking-wide max-w-md mb-12">
              zero-latency audio extraction engine. we decode video content into precision structured data for the ai age.
            </p>
            <button onClick={() => scrollTo('#generator')} className="group inline-flex text-xs uppercase transition-all hover:text-cyan-400 cursor-pointer font-bold text-neutral-300 tracking-[0.2em] border-neutral-700 hover:border-cyan-400 border-b pb-2 items-center gap-2">
              initialize engine
            </button>
          </div>

          <div className="text-left md:text-right reveal-text delay-100">
            <h1 className="md:text-[9vw] lg:text-[10vw] lowercase leading-[0.8] text-6xl font-semibold bg-gradient-to-r from-white via-cyan-200 to-purple-200 bg-clip-text text-transparent tracking-tighter">
              precision<br />transcription<br />ecosystem
            </h1>
          </div>
        </div>

        <div className="flex reveal-text delay-200 w-full pt-8 pb-8 items-center justify-between">
          <div className="flex gap-16">
            <div className="hidden md:block">
              <span className="text-xs font-medium tracking-widest lowercase flex items-center gap-3 text-neutral-400">
                <span className="w-2 h-2 bg-gradient-to-r from-cyan-400 to-purple-400 rounded-full animate-pulse shadow-[0_0_10px_rgba(0,212,255,0.5)]"></span>
                engine edition 2.0.4
              </span>
            </div>
          </div>
          <div className="text-xs text-neutral-500 uppercase tracking-[0.3em] font-medium">
            scroll to process
          </div>
        </div>
      </header>

      {/* Manifesto */}
      <section className="bg-[#000000] px-6 md:px-12 py-40 flex justify-center items-center relative z-10">
        <h2 className="text-3xl md:text-5xl lg:text-6xl font-semibold leading-[1.1] tracking-tighter text-white text-center max-w-5xl">
          Manual labor is a relic. <span className="bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">We provide zero-latency transcription</span> for the next generation of building.
        </h2>
      </section>

      {/* Horizontal Carousel Section */}
      <section id="features" ref={workSectionRef} className="relative h-[250vh] bg-[#000000] z-0">
        <div className="sticky overflow-hidden flex flex-col bg-[#000000] w-full h-screen top-0 justify-center">
          <div className="absolute top-0 left-0 w-full px-6 md:px-12 pt-20 flex justify-between items-start z-10 pointer-events-none">
            <span className="block text-xs font-semibold tracking-[0.3em] uppercase text-neutral-400 font-geist">Systems Analysis</span>
            <span className="block text-xs font-semibold tracking-[0.3em] uppercase text-neutral-400 font-geist">Technical Specs</span>
          </div>

          <div ref={trackRef} className="flex -space-x-12 will-change-transform md:pl-24 md:-space-x-32 w-max pt-20 pb-20 pl-8 items-center">
            {/* Feature 1 - Cyan Gradient */}
            <article className="group shrink-0 cursor-pointer transition-all duration-700 md:w-[45vw] w-[85vw] relative">
              <div className="aspect-[16/9] overflow-hidden bg-gradient-to-br from-cyan-500/20 via-cyan-600/10 to-transparent w-full border-cyan-500/20 border-2 rounded-lg relative flex items-center justify-center group-hover:border-cyan-400/40 transition-all duration-700 group-hover:shadow-[0_0_30px_rgba(0,212,255,0.3)]">
                <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
                <span className="text-9xl relative z-10">🌐</span>
              </div>
              <div className="mt-8 flex items-start justify-between px-2">
                <div>
                  <h3 className="lowercase transition-colors group-hover:bg-gradient-to-r group-hover:from-cyan-400 group-hover:to-cyan-600 group-hover:bg-clip-text group-hover:text-transparent md:text-4xl text-2xl font-semibold text-white tracking-tighter">Multi-Platform</h3>
                  <p className="lowercase text-sm font-medium text-neutral-400 tracking-wide mt-3 uppercase">YouTube & Vimeo native extraction</p>
                </div>
              </div>
            </article>

            {/* Feature 2 - Purple Gradient */}
            <article className="group relative w-[85vw] shrink-0 cursor-pointer transition-all duration-700 md:w-[45vw]">
              <div className="aspect-[16/9] overflow-hidden bg-gradient-to-br from-purple-500/20 via-purple-600/10 to-transparent w-full border-purple-500/20 border-2 rounded-lg relative flex items-center justify-center group-hover:border-purple-400/40 transition-all duration-700 group-hover:shadow-[0_0_30px_rgba(168,85,247,0.3)]">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
                <span className="text-9xl relative z-10">📄</span>
              </div>
              <div className="mt-8 flex items-start justify-between px-2">
                <div>
                  <h3 className="lowercase transition-colors group-hover:bg-gradient-to-r group-hover:from-purple-400 group-hover:to-purple-600 group-hover:bg-clip-text group-hover:text-transparent md:text-4xl text-2xl font-semibold text-white tracking-tighter">Archival Export</h3>
                  <p className="mt-3 text-sm font-medium lowercase tracking-wide text-neutral-400 uppercase">Seamless TXT, DOCX, & PDF delivery</p>
                </div>
              </div>
            </article>

            {/* Feature 3 - Pink Gradient */}
            <article className="group relative w-[85vw] shrink-0 cursor-pointer transition-all duration-700 md:w-[45vw]">
              <div className="relative aspect-[16/9] w-full overflow-hidden bg-gradient-to-br from-pink-500/20 via-pink-600/10 to-transparent border-pink-500/20 border-2 rounded-lg flex items-center justify-center group-hover:border-pink-400/40 transition-all duration-700 group-hover:shadow-[0_0_30px_rgba(236,72,153,0.3)]">
                <div className="absolute inset-0 bg-gradient-to-br from-pink-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
                <span className="text-9xl relative z-10">🤖</span>
              </div>
              <div className="mt-8 flex items-start justify-between px-2">
                <div>
                  <h3 className="lowercase transition-colors group-hover:bg-gradient-to-r group-hover:from-pink-400 group-hover:to-pink-600 group-hover:bg-clip-text group-hover:text-transparent md:text-4xl text-2xl font-semibold text-white tracking-tighter">AI Analysis</h3>
                  <p className="mt-3 text-sm font-medium lowercase tracking-wide text-neutral-400 uppercase">Smart contextual summarization engine</p>
                </div>
              </div>
            </article>
          </div>

          <div className="absolute bottom-20 left-6 md:left-12 w-48 h-[1px] bg-neutral-900 overflow-hidden">
            <div ref={progressBarRef} className="h-full bg-white w-0"></div>
          </div>
        </div>
      </section>

      {/* Bot Demo Section - Colorful Showcase */}
      <section id="demo" className="py-20 md:py-32 relative z-10 bg-gradient-to-b from-black via-purple-950/10 to-black">
        <div className="w-full max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-6xl font-bold tracking-tighter mb-4 bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              telegram bot in action
            </h2>
            <p className="text-neutral-400 text-sm uppercase tracking-widest font-medium">instant processing / zero friction</p>
          </div>
          <BotDemo />
        </div>
      </section>

      {/* Generator Section */}
      <section id="generator" className="relative z-10 bg-[#000000] border-t border-neutral-900">
        <Generator />
      </section>

      {/* Method Section */}
      <section id="studio" className="relative z-20 pt-20 bg-[#000000]">
        <div className="md:py-40 md:px-12 text-[#fcfbf9] border-neutral-900 border-t pt-24 pr-6 pb-24 pl-6">
          <div className="max-w-7xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-20 lg:gap-40">
              <div className="">
                <h3 className="md:text-5xl lg:text-6xl lowercase leading-tight text-4xl font-semibold tracking-tighter mb-10 font-geist bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">The Method</h3>
                <div className="w-20 h-[2px] mb-12 bg-gradient-to-r from-cyan-400 to-purple-400"></div>
                <p className="uppercase text-sm text-neutral-400 tracking-[0.3em] font-bold">Technical Architecture</p>
              </div>
              <div className="flex flex-col justify-between h-full">
                <p className="md:text-xl leading-relaxed lowercase text-lg font-light text-neutral-300 tracking-tight max-w-xl mb-4">
                  we bridge the gap between multimedia content and usable data. using the latest in neural linguistics, we extract not just words, but meaning.
                </p>

                <div className="grid grid-cols-2 gap-16 border-neutral-900 border-t mt-24 pt-16">
                  <div className="">
                    <span className="block text-sm uppercase font-bold text-white tracking-[0.2em] mb-8">Operations</span>
                    <ul className="space-y-4 text-sm font-medium lowercase text-neutral-300 tracking-wider">
                      <li className="flex gap-4 items-center">
                        <span className="text-white">v3:</span> whisper-powered
                      </li>
                      <li className="flex gap-4 items-center">
                        <span className="text-white">latency:</span> {"<100ms"}
                      </li>
                      <li className="flex gap-4 items-center">
                        <span className="text-white">output:</span> precision
                      </li>
                    </ul>
                  </div>
                  <div className="">
                    <span className="block text-sm uppercase font-bold text-white tracking-[0.2em] mb-8">Integration</span>
                    <ul className="lowercase text-sm font-medium text-neutral-300 space-y-4 tracking-wider">
                      <li className="">FastAPI Core</li>
                      <li className="">Next.js 16.1</li>
                      <li className="">Vercel Edge</li>
                      <li className="">AI Pipelines</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Minimal Footer */}
          <footer id="contact" className="mt-40 pt-32 border-t border-neutral-900">
            <div className="max-w-7xl mx-auto">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-20">
                <div className="max-w-3xl">
                  <h4 className="text-5xl md:text-6xl lg:text-7xl font-semibold tracking-tighter lowercase mb-12 bg-gradient-to-r from-white to-cyan-200 bg-clip-text text-transparent">
                    optimize<br />your delivery.
                  </h4>
                  <a href="https://t.me/TranscriptFlowBot" target="_blank" className="inline-flex items-center gap-4 md:text-3xl transition-all lowercase hover:text-cyan-400 hover:border-cyan-400 group text-2xl font-semibold text-neutral-300 border-neutral-700 border-b-2 pb-3 font-geist">
                    launch telegram bot
                  </a>
                </div>

                <div className="flex flex-col items-start md:items-end gap-10 w-full md:w-auto">
                  <div className="flex gap-6">
                    <a href="https://github.com/dpeluola" target="_blank" className="text-neutral-400 hover:text-cyan-400 transition-colors duration-500">
                      <iconify-icon icon="simple-icons:github" width="24"></iconify-icon>
                    </a>
                    <a href="#" className="text-neutral-400 hover:text-purple-400 transition-colors duration-500">
                      <iconify-icon icon="simple-icons:blueprint" width="24"></iconify-icon>
                    </a>
                  </div>
                  <span className="text-xs font-semibold uppercase tracking-[0.4em] text-neutral-500 font-geist">
                    © 2026 TF_ECOSYSTEM
                  </span>
                </div>
              </div>
            </div>
          </footer>
        </div>
      </section>
    </div>
  );
}
