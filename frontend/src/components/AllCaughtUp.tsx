import { Link } from 'react-router-dom';

interface AllCaughtUpProps {
  completedToday: number;
  completedThisWeek: number;
}

export function AllCaughtUp({ completedToday, completedThisWeek }: AllCaughtUpProps) {
  return (
    <div className="flex flex-col items-center animate-fade-in max-w-4xl mx-auto pt-8 sm:pt-16 md:pt-24 px-4 min-h-[calc(100vh-80px)]">
      <div className="text-center space-y-4 mb-12">
        <div className="text-6xl mb-2">🎉</div>
        <p className="text-gray-400 text-sm font-medium tracking-wide uppercase">All done</p>
        <h1 className="font-sans font-bold text-5xl sm:text-6xl md:text-[72px] leading-tight tracking-tight text-[#001a41]">
          You're all <span className="text-[#0066cc]">caught up.</span>
        </h1>
        <p className="text-gray-400 text-base md:text-lg max-w-lg mx-auto leading-relaxed">
          No pending tasks — great work. Add something new to keep the momentum going.
        </p>
      </div>

      {(completedToday > 0 || completedThisWeek > 0) && (
        <div className="w-full max-w-sm grid grid-cols-2 gap-6 bg-white/50 p-6 rounded-3xl border border-gray-100/50 mb-10">
          <div className="flex flex-col items-center">
            <div className="text-3xl sm:text-4xl font-bold text-[#001a41] mb-1 leading-none">{completedToday}</div>
            <div className="text-gray-400 text-[10px] font-bold uppercase tracking-[0.2em] text-center">Done today</div>
          </div>
          <div className="flex flex-col items-center border-l border-gray-100 pl-6">
            <div className="text-3xl sm:text-4xl font-bold text-[#001a41] mb-1 leading-none">{completedThisWeek}</div>
            <div className="text-gray-400 text-[10px] font-bold uppercase tracking-[0.2em] text-center">This week</div>
          </div>
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3">
        <Link
          to="/add"
          className="bg-[#001a41] hover:bg-black text-white px-8 py-3.5 rounded-2xl text-[15px] font-bold shadow-[0_20px_40px_rgba(0,26,65,0.15)] transition-all hover:scale-[1.02] active:scale-[0.98] text-center"
        >
          Add new tasks
        </Link>
        <Link
          to="/browse?status=completed"
          className="bg-white hover:bg-gray-50 text-[#001a41] px-8 py-3.5 rounded-2xl text-[15px] font-bold border border-gray-200 transition-all hover:scale-[1.02] active:scale-[0.98] text-center"
        >
          Browse completed
        </Link>
      </div>
    </div>
  );
}
