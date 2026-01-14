import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getPresentation, executeCode, resetPresentationSession, type Slide, type CodeExecutionResult } from '../api/client';

// Simple markdown renderer (basic support for headers, bold, code, lists, tables)
function renderMarkdown(content: string): string {
  let html = content
    // Headers
    .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mt-4 mb-2 text-cyan-300">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold mt-4 mb-2 text-cyan-200">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold mt-4 mb-3 text-white">$1</h1>')
    // Bold and italic
    .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-amber-300">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em class="italic">$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="bg-gray-800 px-1.5 py-0.5 rounded text-pink-300 font-mono text-sm">$1</code>')
    // Block quotes
    .replace(/^> (.+)$/gm, '<blockquote class="border-l-4 border-cyan-500 pl-4 py-2 my-3 bg-gray-800/50 rounded-r italic text-gray-300">$1</blockquote>')
    // Horizontal rules
    .replace(/^---$/gm, '<hr class="my-6 border-gray-700" />')
    // List items
    .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc text-gray-300">$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal text-gray-300">$1</li>')
    // Tables (simple)
    .replace(/\|(.+)\|/g, (match) => {
      const cells = match.split('|').filter(c => c.trim());
      if (cells.every(c => c.trim().match(/^-+$/))) {
        return ''; // Skip separator row
      }
      const isHeader = match.includes('**') || cells[0].trim().startsWith('**');
      const cellTag = isHeader ? 'th' : 'td';
      const cellClass = isHeader 
        ? 'px-3 py-2 text-left font-semibold text-cyan-300 bg-gray-800' 
        : 'px-3 py-2 text-left text-gray-300 border-t border-gray-700';
      return `<tr>${cells.map(c => `<${cellTag} class="${cellClass}">${c.trim().replace(/\*\*/g, '')}</${cellTag}>`).join('')}</tr>`;
    })
    // LaTeX-style math (basic)
    .replace(/\$\$(.+?)\$\$/g, '<div class="my-4 p-3 bg-gray-800 rounded text-center font-mono text-cyan-300">$1</div>')
    .replace(/\$(.+?)\$/g, '<span class="font-mono text-cyan-300">$1</span>')
    // Code blocks
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="bg-gray-900 p-4 rounded-lg my-4 overflow-x-auto"><code class="text-sm font-mono text-green-300">$2</code></pre>')
    // Paragraphs (wrap remaining text)
    .replace(/\n\n/g, '</p><p class="my-2 text-gray-300">')
    // Line breaks
    .replace(/\n/g, '<br />');
  
  // Wrap tables
  html = html.replace(/(<tr>[\s\S]*?<\/tr>)+/g, '<table class="w-full my-4 border-collapse">$&</table>');
  
  // Wrap list items
  html = html.replace(/(<li[^>]*>[\s\S]*?<\/li>)+/g, '<ul class="my-3">$&</ul>');
  
  return `<div class="prose prose-invert max-w-none">${html}</div>`;
}

// Code editor component with syntax highlighting
function CodeEditor({ 
  code, 
  onChange, 
  readOnly = false 
}: { 
  code: string; 
  onChange?: (code: string) => void;
  readOnly?: boolean;
}) {
  return (
    <div className="relative h-full">
      <textarea
        value={code}
        onChange={(e) => onChange?.(e.target.value)}
        readOnly={readOnly}
        className="w-full h-full bg-gray-900 text-green-400 font-mono text-sm p-4 rounded-lg 
                   border border-gray-700 focus:border-cyan-500 focus:outline-none resize-none
                   leading-relaxed"
        spellCheck={false}
        style={{ tabSize: 4 }}
      />
    </div>
  );
}

// Output display component
function OutputDisplay({ result }: { result: CodeExecutionResult | null }) {
  if (!result) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 italic">
        Run code to see output...
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      {/* Text Output */}
      {result.output && (
        <pre className="bg-gray-900 p-4 rounded-lg text-sm font-mono text-gray-300 whitespace-pre-wrap mb-4">
          {result.output}
        </pre>
      )}
      
      {/* Error Output */}
      {result.error && (
        <pre className="bg-red-900/30 border border-red-700 p-4 rounded-lg text-sm font-mono text-red-300 whitespace-pre-wrap mb-4">
          {result.error}
        </pre>
      )}
      
      {/* Figures */}
      {result.figures.map((fig, idx) => (
        <div key={idx} className="mb-4">
          <img 
            src={fig} 
            alt={`Figure ${idx + 1}`} 
            className="max-w-full rounded-lg border border-gray-700"
          />
        </div>
      ))}
      
      {/* Success indicator */}
      {result.success && !result.output && !result.error && result.figures.length === 0 && (
        <div className="text-green-400 italic">✓ Code executed successfully (no output)</div>
      )}
    </div>
  );
}

// Slide content component
function SlideContent({ slide }: { slide: Slide }) {
  return (
    <div className="h-full overflow-auto p-6">
      {/* Slide type badge */}
      <div className="mb-4">
        <span className={`
          px-2 py-1 rounded text-xs font-medium uppercase tracking-wide
          ${slide.type === 'title' ? 'bg-purple-900 text-purple-200' : ''}
          ${slide.type === 'concept' ? 'bg-blue-900 text-blue-200' : ''}
          ${slide.type === 'code' ? 'bg-green-900 text-green-200' : ''}
          ${slide.type === 'summary' ? 'bg-amber-900 text-amber-200' : ''}
          ${slide.type === 'closing' ? 'bg-pink-900 text-pink-200' : ''}
        `}>
          {slide.type}
        </span>
      </div>
      
      {/* Slide content */}
      <div 
        className="text-gray-200"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(slide.content) }}
      />
      
      {/* Speaker notes */}
      {slide.notes && (
        <div className="mt-6 pt-4 border-t border-gray-700">
          <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">Speaker Notes</div>
          <p className="text-sm text-gray-400 italic">{slide.notes}</p>
        </div>
      )}
    </div>
  );
}

export function PresentationPage() {
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [editableCode, setEditableCode] = useState('');
  const [executionResult, setExecutionResult] = useState<CodeExecutionResult | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  // Fetch presentation data
  const { data: presentation, isLoading, error } = useQuery({
    queryKey: ['presentation'],
    queryFn: getPresentation,
  });

  // Execute code mutation
  const executeMutation = useMutation({
    mutationFn: (code: string) => executeCode(code),
    onSuccess: (result) => {
      setExecutionResult(result);
      setIsExecuting(false);
    },
    onError: (error) => {
      setExecutionResult({
        success: false,
        output: '',
        error: error instanceof Error ? error.message : 'Unknown error',
        figures: [],
      });
      setIsExecuting(false);
    },
  });

  // Reset session mutation
  const resetMutation = useMutation({
    mutationFn: () => resetPresentationSession(),
    onSuccess: () => {
      setExecutionResult(null);
    },
  });

  const currentSlide = presentation?.slides[currentSlideIndex];

  // Update editable code when slide changes
  useEffect(() => {
    if (currentSlide?.code) {
      setEditableCode(currentSlide.code);
      setExecutionResult(null);
    }
  }, [currentSlide]);

  // Keyboard navigation
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!presentation) return;
    
    if (e.key === 'ArrowRight' || e.key === ' ') {
      e.preventDefault();
      setCurrentSlideIndex(prev => Math.min(prev + 1, presentation.slides.length - 1));
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setCurrentSlideIndex(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && e.shiftKey && currentSlide?.code) {
      e.preventDefault();
      handleRunCode();
    }
  }, [presentation, currentSlide]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const handleRunCode = () => {
    if (!editableCode.trim()) return;
    setIsExecuting(true);
    executeMutation.mutate(editableCode);
  };

  const handleResetSession = () => {
    resetMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-cyan-400 text-xl">Loading presentation...</div>
      </div>
    );
  }

  if (error || !presentation) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-red-400 text-xl">
          Error loading presentation: {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-cyan-400">{presentation.title}</h1>
          <p className="text-sm text-gray-500">{presentation.subtitle}</p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-gray-400">
            Slide {currentSlideIndex + 1} / {presentation.slides.length}
          </span>
          <button
            onClick={handleResetSession}
            className="px-3 py-1 text-sm bg-gray-800 hover:bg-gray-700 rounded text-gray-300"
          >
            Reset Session
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex">
        {/* Left panel: Slide content */}
        <div className="w-1/2 border-r border-gray-800 flex flex-col">
          <div className="bg-gray-900 px-4 py-2 border-b border-gray-800 flex items-center justify-between">
            <h2 className="font-medium text-gray-300">
              {currentSlide?.title}
            </h2>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentSlideIndex(prev => Math.max(prev - 1, 0))}
                disabled={currentSlideIndex === 0}
                className="px-3 py-1 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-sm"
              >
                ← Prev
              </button>
              <button
                onClick={() => setCurrentSlideIndex(prev => Math.min(prev + 1, presentation.slides.length - 1))}
                disabled={currentSlideIndex === presentation.slides.length - 1}
                className="px-3 py-1 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-sm"
              >
                Next →
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-hidden">
            {currentSlide && <SlideContent slide={currentSlide} />}
          </div>
        </div>

        {/* Right panel: Code + Output */}
        <div className="w-1/2 flex flex-col">
          {currentSlide?.code ? (
            <>
              {/* Code editor */}
              <div className="flex-1 flex flex-col border-b border-gray-800">
                <div className="bg-gray-900 px-4 py-2 border-b border-gray-800 flex items-center justify-between">
                  <span className="text-sm text-gray-400 font-mono">Python Code</span>
                  <button
                    onClick={handleRunCode}
                    disabled={isExecuting}
                    className="px-4 py-1 bg-green-700 hover:bg-green-600 disabled:bg-gray-700 
                             rounded text-sm font-medium flex items-center gap-2"
                  >
                    {isExecuting ? (
                      <>
                        <span className="animate-spin">⏳</span> Running...
                      </>
                    ) : (
                      <>▶ Run (Shift+Enter)</>
                    )}
                  </button>
                </div>
                <div className="flex-1 p-2">
                  <CodeEditor
                    code={editableCode}
                    onChange={setEditableCode}
                  />
                </div>
              </div>

              {/* Output */}
              <div className="flex-1 flex flex-col">
                <div className="bg-gray-900 px-4 py-2 border-b border-gray-800">
                  <span className="text-sm text-gray-400">Output</span>
                </div>
                <div className="flex-1 p-4 overflow-auto">
                  <OutputDisplay result={executionResult} />
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-600">
              <div className="text-center">
                <div className="text-4xl mb-4">📝</div>
                <p>This slide has no code</p>
                <p className="text-sm mt-2">Navigate to a code slide to see the editor</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Slide thumbnails */}
      <div className="bg-gray-900 border-t border-gray-800 px-4 py-3 overflow-x-auto">
        <div className="flex gap-2">
          {presentation.slides.map((slide, idx) => (
            <button
              key={slide.id}
              onClick={() => setCurrentSlideIndex(idx)}
              className={`
                flex-shrink-0 w-24 h-16 rounded border-2 transition-all
                flex items-center justify-center text-xs font-medium
                ${idx === currentSlideIndex 
                  ? 'border-cyan-500 bg-cyan-900/30 text-cyan-300' 
                  : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'}
                ${slide.code ? 'ring-1 ring-green-700' : ''}
              `}
            >
              <div className="text-center px-1">
                <div className="text-[10px] text-gray-500">{idx + 1}</div>
                <div className="truncate w-20">{slide.title.slice(0, 15)}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Keyboard shortcuts hint */}
      <div className="bg-gray-950 px-4 py-2 text-xs text-gray-600 flex gap-6 justify-center">
        <span>← → Navigate slides</span>
        <span>Shift+Enter Run code</span>
        <span>Space Next slide</span>
      </div>
    </div>
  );
}

export default PresentationPage;

