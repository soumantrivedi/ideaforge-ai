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
}

export function ResizableProductLifecycleSidebar({
  productId,
  phases,
  submissions,
  currentPhaseId,
  onPhaseSelect,
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

  if (!productId) {
    return null;
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

