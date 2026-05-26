import { useWebSocket } from './hooks/useWebSocket';
import { PixelTownPage } from './features/pixel-town/PixelTownPage';
import { Component, type ReactNode } from 'react';

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 20, color: '#f8e8d4', background: '#1a1a2e', height: '100vh' }}>
          <h2 style={{ color: '#e94560' }}>Pixel AI Town Error</h2>
          <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>{this.state.error.message}</pre>
          <pre style={{ fontSize: 10, color: '#888' }}>{this.state.error.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  useWebSocket();

  return (
    <ErrorBoundary>
      <PixelTownPage />
    </ErrorBoundary>
  );
}
