interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}

const sizeClasses = {
  sm: 'w-4 h-4 border-2',
  md: 'w-8 h-8 border-2',
  lg: 'w-12 h-12 border-3',
};

export function LoadingSpinner({ size = 'md', text }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <div
        className={`${sizeClasses[size]} border-[var(--karma-border)] border-t-[var(--karma-accent)] rounded-full animate-spin`}
      />
      {text && (
        <p className="text-[var(--karma-text-muted)] text-sm animate-pulse">
          {text}
        </p>
      )}
    </div>
  );
}

