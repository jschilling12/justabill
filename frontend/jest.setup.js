import '@testing-library/jest-dom';

// Mock next/router
jest.mock('next/router', () => ({
  useRouter() {
    return {
      route: '/',
      pathname: '/',
      query: {},
      asPath: '/',
      push: jest.fn(),
      replace: jest.fn(),
      isReady: true,
    };
  },
}));

// Mock next/link
jest.mock('next/link', () => {
  const MockLink = function(props) {
    return <a href={props.href} {...props}>{props.children}</a>;
  };
  MockLink.displayName = 'MockLink';
  return MockLink;
});

// Mock IntersectionObserver
class MockIntersectionObserver {
  observe = jest.fn();
  disconnect = jest.fn();
  unobserve = jest.fn();
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});

// Mock scrollTo and scrollBy
Element.prototype.scrollTo = jest.fn();
Element.prototype.scrollBy = jest.fn();

// Mock getBoundingClientRect
Element.prototype.getBoundingClientRect = jest.fn(() => ({
  width: 1000,
  height: 400,
  top: 0,
  left: 0,
  bottom: 400,
  right: 1000,
  x: 0,
  y: 0,
  toJSON: () => {},
}));
