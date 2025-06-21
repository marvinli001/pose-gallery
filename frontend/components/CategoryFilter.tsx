'use client';

import { useEffect, useState } from 'react';
import { searchAPI } from '@/lib/api';
import { Category } from '@/lib/types';

interface CategoryFilterProps {
  selected?: string;
  onChange: (category: string) => void;
}

export default function CategoryFilter({ selected, onChange }: CategoryFilterProps) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    searchAPI.getCategories()
      .then(setCategories)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex gap-2 overflow-x-auto py-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-10 w-24 bg-gray-200 rounded-full animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex gap-2 overflow-x-auto py-4 scrollbar-hide">
      <button
        onClick={() => onChange('')}
        className={`px-4 py-2 rounded-full whitespace-nowrap transition-colors ${
          !selected 
            ? 'bg-blue-600 text-white' 
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
        }`}
      >
        全部
      </button>
      {categories.map((category) => (
        <button
          key={category.name}
          onClick={() => onChange(category.name)}
          className={`px-4 py-2 rounded-full whitespace-nowrap transition-colors ${
            selected === category.name
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          {category.name} ({category.count})
        </button>
      ))}
    </div>
  );
}
