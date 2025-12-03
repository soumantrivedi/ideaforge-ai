import { useState, useRef, useEffect } from 'react';
import { ProductLifecycleSidebar } from './ProductLifecycleSidebar';
import { MyProgress } from './MyProgress';
import type { LifecyclePhase, PhaseSubmission } from '../lib/product-lifecycle-service';

interface ResizableProductLifecycleSidebarProps {
  productId: string;
  phases: LifecyclePhase[];
  submissions: PhaseSubmission[];
  currentPhaseId?: string;
  onPhaseSelect: (phase: LifecyclePhase) => void;
  phasesLoading?: boolean;
}

export function ResizableProductLifecycleSidebar({
  productId,
  phases,
  submissions,
  currentPhaseId,
  onPhaseSelect,
  phasesLoading = false,
}: ResizableProductLifecycleSidebarProps) {
  const [width, setWidth] = useState(360); // Default ~25% of 1440px screen
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef<number>(0);
  const startWidthRef = useRef<number>(0);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      
      const deltaX = e.clientX - startXRef.current;
      const newWidth = Math.max(200, Math.min(window.innerWidth * 0.25, startWidthRef.current + deltaX));
      setWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = width;
  };

  // Don't hide sidebar if productId is temporarily empty during state restoration
  // Only hide if productId is explicitly empty and we're not loading
  // This prevents flickering during refresh
  if (!productId && !phasesLoading) {
    return null;
  }
  
  // Show loading state if productId exists but phases are loading
  if (productId && phasesLoading && (!phases || phases.length === 0)) {
    return (
      <div className="hidden lg:block relative z-10" style={{ width: `${width}px`, minWidth: '200px', maxWidth: '25%' }}>
        <div className="sticky top-0 h-[calc(100vh-8rem)] overflow-y-auto flex flex-col gap-4 bg-white border-r border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-bold text-gray-900 mb-2">Product Lifecycle</h2>
            <div className="text-center py-8">
              <p className="text-sm text-gray-500">Loading phases...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={sidebarRef}
      className="hidden lg:block relative z-10"
      style={{ width: `${width}px`, minWidth: '200px', maxWidth: '25%' }}
    >
      <div className="sticky top-0 h-[calc(100vh-8rem)] overflow-y-auto flex flex-col gap-4">
        <ProductLifecycleSidebar
          phases={phases}
          submissions={submissions}
          currentPhaseId={currentPhaseId}
          onPhaseSelect={onPhaseSelect}
          productId={productId}
          phasesLoading={phasesLoading}
        />
        <div className="flex-shrink-0">
          <MyProgress
            productId={productId}
            onNavigateToPhase={(phaseId) => {
              const phase = phases.find(p => p.id === phaseId);
              if (phase) {
                onPhaseSelect(phase);
              }
            }}
          />
        </div>
      </div>
      {/* Resize Handle */}
      <div
        onMouseDown={handleMouseDown}
        className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500 transition-colors z-10"
        style={{ backgroundColor: isResizing ? '#3b82f6' : 'transparent' }}
      />
    </div>
  );
}

