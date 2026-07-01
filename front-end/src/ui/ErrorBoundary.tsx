/**
 * Top-level React error boundary.
 *
 * Catches render-time errors anywhere in the wrapped subtree and shows a
 * friendly fallback instead of an unstyled blank screen. This only catches
 * errors thrown during rendering / lifecycle methods — it does not catch
 * errors in event handlers or async code (e.g. `useChatStream`'s own
 * try/catch already handles those).
 */
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unhandled UI error:', error, info.componentStack);
  }

  private handleReload = () => {
    this.setState({ hasError: false });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-app flex h-screen w-full flex-col items-center justify-center gap-4 p-6 text-center">
          <p className="text-body-lg font-semibold text-white">Something went wrong.</p>
          <p className="text-body-sm max-w-sm text-white/80">
            The QC Assistant hit an unexpected error. Reloading will start a fresh session.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            className="rounded-xl bg-primary text-on-primary-fixed px-md py-sm text-label-md font-semibold shadow-sm hover:brightness-105"
          >
            Reload
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
