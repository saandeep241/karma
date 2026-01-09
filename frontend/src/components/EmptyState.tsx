import { Link } from 'react-router-dom';

interface EmptyStateProps {
  icon?: string;
  title: string;
  description: string;
  actionLabel?: string;
  actionPath?: string;
  onAction?: () => void;
}

export function EmptyState({
  icon = '📭',
  title,
  description,
  actionLabel,
  actionPath,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="text-center py-12 animate-fade-in">
      <div className="text-6xl mb-4">{icon}</div>
      <h3 className="text-xl font-medium mb-2">{title}</h3>
      <p className="text-[var(--karma-text-muted)] mb-6 max-w-md mx-auto">
        {description}
      </p>
      {actionLabel && (actionPath || onAction) && (
        actionPath ? (
          <Link to={actionPath} className="btn btn-primary no-underline">
            {actionLabel}
          </Link>
        ) : (
          <button onClick={onAction} className="btn btn-primary">
            {actionLabel}
          </button>
        )
      )}
    </div>
  );
}

