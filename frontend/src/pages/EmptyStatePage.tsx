import { useState } from 'react';

const STARTER_CATEGORIES = [
  'Productivity',
  'Personal Development',
  'Home Cleaning',
  'Artistic',
  'Health & Fitness',
  'Finance',
];

export function EmptyStatePage() {
  const [taskInput, setTaskInput] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

  const toggleCategory = (category: string) => {
    setSelectedCategories((prev) =>
      prev.includes(category)
        ? prev.filter((c) => c !== category)
        : [...prev, category]
    );
  };

  return (
    <div className="flex flex-col items-center animate-fade-in max-w-4xl mx-auto pt-8 sm:pt-16 md:pt-24 px-4 min-h-[calc(100vh-80px)]">
      <div className="text-center space-y-4 mb-12">
        <h1 className="font-sans font-bold text-2xl sm:text-3xl text-[#001a41] leading-tight">
          It looks like you don't have any tasks yet.
        </h1>
        <p className="text-gray-400 text-base sm:text-lg leading-relaxed">
          Add tasks to personalize your recommendations.
        </p>
        <p className="text-gray-400 text-xs sm:text-sm leading-relaxed max-w-md mx-auto">
          This app suggests what you can do based on your mood, energy, and available time. Recommendations are generated from the tasks you add. If no tasks are added, suggestions may feel random.
        </p>
      </div>

      <div className="w-full max-w-xl mb-6">
        <label className="block text-xs font-bold uppercase tracking-[0.15em] text-[#001a41] mb-2">
          Add Tasks (Comma-Separated)
        </label>
        <input
          type="text"
          value={taskInput}
          onChange={(e) => setTaskInput(e.target.value)}
          placeholder="e.g. Read a book, Clean the kitchen, Go for a walk"
          className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#0066cc]/10 focus:border-[#0066cc] transition-all text-sm text-gray-700 placeholder-gray-400"
        />
      </div>

      <div className="w-full max-w-xl mb-10">
        <label className="block text-xs font-bold uppercase tracking-[0.15em] text-[#001a41] mb-3">
          Or Pick Starter Categories
        </label>
        <div className="flex flex-wrap gap-2">
          {STARTER_CATEGORIES.map((category) => (
            <button
              key={category}
              onClick={() => toggleCategory(category)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-all ${
                selectedCategories.includes(category)
                  ? 'bg-[#0066cc] text-white border-[#0066cc]'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
              }`}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      <button className="w-full max-w-xl bg-[#0066cc] hover:bg-[#0052a3] text-white py-3.5 rounded-full text-base font-bold transition-all shadow-[0_8px_24px_rgba(0,102,204,0.25)]">
        Save & Continue
      </button>
    </div>
  );
}
