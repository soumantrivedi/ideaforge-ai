import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { LoginPage } from './components/LoginPage';
import { MainApp } from './components/MainApp';
import { ErrorBoundary } from './components/ErrorBoundary';
import { CommandPalette } from './components/CommandPalette';
import { initKeyboardShortcuts } from './lib/keyboard-shortcuts';
import { useEffect } from 'react';

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth();

  // Initialize keyboard shortcuts
  useEffect(() => {
    const cleanup = initKeyboardShortcuts();
    return cleanup;
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={() => {}} />;
  }

  return (
    <>
      <CommandPalette />
      <MainApp />
    </>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
