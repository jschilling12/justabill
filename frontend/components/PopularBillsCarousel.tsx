import { useRef, useEffect, useCallback, useState } from 'react';
import Link from 'next/link';
import { Bill } from '../lib/api';

interface PopularBillsCarouselProps {
  bills: Bill[];
  renderVotePreview: (billId: string) => React.ReactNode;
}

export default function PopularBillsCarousel({ bills, renderVotePreview }: PopularBillsCarouselProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [showLeftArrow, setShowLeftArrow] = useState(false);
  const [showRightArrow, setShowRightArrow] = useState(true);

  // Card width + gap (320px card + 16px gap)
  const CARD_WIDTH = 336;
  const SCROLL_AMOUNT = CARD_WIDTH;

  // Update arrow visibility based on scroll position
  const updateArrowVisibility = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const { scrollLeft, scrollWidth, clientWidth } = container;
    setShowLeftArrow(scrollLeft > 10);
    setShowRightArrow(scrollLeft < scrollWidth - clientWidth - 10);
  }, []);

  // Handle horizontal mouse wheel scrolling
  const handleWheel = useCallback((e: WheelEvent) => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // Only intercept if primarily vertical scroll (we convert to horizontal)
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      e.preventDefault();
      container.scrollBy({
        left: e.deltaY,
        behavior: 'smooth'
      });
    }
  }, []);

  // Attach wheel listener
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    container.addEventListener('wheel', handleWheel, { passive: false });
    container.addEventListener('scroll', updateArrowVisibility);
    updateArrowVisibility();

    return () => {
      container.removeEventListener('wheel', handleWheel);
      container.removeEventListener('scroll', updateArrowVisibility);
    };
  }, [handleWheel, updateArrowVisibility]);

  // Auto-scroll effect (pauses on hover)
  useEffect(() => {
    if (isPaused || bills.length <= 3) return;

    const container = scrollContainerRef.current;
    if (!container) return;

    const interval = setInterval(() => {
      const { scrollLeft, scrollWidth, clientWidth } = container;
      const maxScroll = scrollWidth - clientWidth;

      if (scrollLeft >= maxScroll - 10) {
        // Reset to beginning for loop effect
        container.scrollTo({ left: 0, behavior: 'smooth' });
      } else {
        container.scrollBy({ left: CARD_WIDTH, behavior: 'smooth' });
      }
    }, 4000); // Auto-scroll every 4 seconds

    return () => clearInterval(interval);
  }, [isPaused, bills.length, CARD_WIDTH]);

  const scrollLeft = () => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const { scrollLeft: currentScroll } = container;
    if (currentScroll <= 10) {
      // Loop to end
      container.scrollTo({ left: container.scrollWidth, behavior: 'smooth' });
    } else {
      container.scrollBy({ left: -SCROLL_AMOUNT, behavior: 'smooth' });
    }
  };

  const scrollRight = () => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const { scrollLeft, scrollWidth, clientWidth } = container;
    const maxScroll = scrollWidth - clientWidth;

    if (scrollLeft >= maxScroll - 10) {
      // Loop to beginning
      container.scrollTo({ left: 0, behavior: 'smooth' });
    } else {
      container.scrollBy({ left: SCROLL_AMOUNT, behavior: 'smooth' });
    }
  };

  return (
    <div 
      className="relative group"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Left Arrow */}
      <button
        onClick={scrollLeft}
        className={`absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-white/90 hover:bg-white shadow-lg rounded-full p-2 transition-all duration-200 ${
          showLeftArrow ? 'opacity-100' : 'opacity-0 pointer-events-none'
        } group-hover:opacity-100`}
        aria-label="Scroll left"
      >
        <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Right Arrow */}
      <button
        onClick={scrollRight}
        className={`absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-white/90 hover:bg-white shadow-lg rounded-full p-2 transition-all duration-200 ${
          showRightArrow ? 'opacity-100' : 'opacity-0 pointer-events-none'
        } group-hover:opacity-100`}
        aria-label="Scroll right"
      >
        <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {/* Scrollable Container */}
      <div
        ref={scrollContainerRef}
        className="flex gap-4 overflow-x-auto scrollbar-hide scroll-smooth px-1 py-2"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        data-testid="carousel-container"
      >
        {bills.map((bill, index) => (
          <Link
            key={bill.id}
            href={`/bills/${bill.id}`}
            className={`flex-shrink-0 w-80 block rounded-xl shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-1 ${
              index === 0 
                ? 'bg-gradient-to-br from-orange-50 to-red-50 border-2 border-orange-200' 
                : 'bg-white border border-gray-200'
            }`}
            data-testid="carousel-card"
          >
            <div className="p-5">
              <div className="flex items-center justify-between mb-2">
                <span className={`text-2xl ${index === 0 ? '' : 'opacity-70'}`}>
                  🔥
                </span>
                {bill.popularity_score && bill.popularity_score > 0 && (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-orange-100 text-orange-800">
                    🔥 {bill.popularity_score} mentions
                  </span>
                )}
              </div>
              <h3 className="font-bold text-gray-900 text-base">
                {bill.bill_type.toUpperCase()}. {bill.bill_number}
              </h3>
              <p className="mt-1 text-sm text-gray-700 line-clamp-3">
                {bill.title || 'Untitled'}
              </p>
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-gray-500 capitalize">
                  {bill.status?.replace(/_/g, ' ') || 'Status unknown'}
                </span>
                <span className="text-xs font-medium text-blue-600 flex items-center gap-1">
                  Vote now →
                </span>
              </div>
              <div className="mt-2">
                {renderVotePreview(bill.id)}
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Scroll Indicator Dots */}
      {bills.length > 3 && (
        <div className="flex justify-center mt-3 gap-1.5">
          {bills.map((_, index) => (
            <button
              key={index}
              onClick={() => {
                const container = scrollContainerRef.current;
                if (container) {
                  container.scrollTo({ left: index * CARD_WIDTH, behavior: 'smooth' });
                }
              }}
              className="w-2 h-2 rounded-full bg-gray-300 hover:bg-orange-400 transition-colors"
              aria-label={`Go to slide ${index + 1}`}
              data-testid="carousel-dot"
            />
          ))}
        </div>
      )}
    </div>
  );
}
