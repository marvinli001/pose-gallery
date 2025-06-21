// components/PoseCard.tsx
'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Pose } from '@/lib/types';

interface PoseCardProps {
  pose: Pose;
  onClick: () => void;
}

export default function PoseCard({ pose, onClick }: PoseCardProps) {
  const [imageError, setImageError] = useState(false);
  const [loading, setLoading] = useState(true);

  return (
    <div
      onClick={onClick}
      className="group cursor-pointer bg-white rounded-lg overflow-hidden shadow-sm hover:shadow-lg transition-shadow"
    >
      <div className="relative aspect-[3/4] bg-gray-100">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
          </div>
        )}
        
        <Image
          src={imageError ? '/placeholder.svg' : (pose.thumbnail_url || pose.oss_url)}
          alt={pose.title}
          fill
          sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
          className={`object-cover transition-opacity duration-300 ${
            loading ? 'opacity-0' : 'opacity-100'
          }`}
          onLoad={() => setLoading(false)}
          onError={() => {
            setImageError(true);
            setLoading(false);
          }}
        />
        
        {/* 悬停遮罩 */}
        <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-opacity" />
        
        {/* 角标 */}
        {pose.scene_category && (
          <div className="absolute top-2 left-2 px-2 py-1 bg-black bg-opacity-50 text-white text-xs rounded">
            {pose.scene_category}
          </div>
        )}
        
        {/* 浏览次数 */}
        <div className="absolute bottom-2 right-2 px-2 py-1 bg-black bg-opacity-50 text-white text-xs rounded flex items-center gap-1">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
            <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
          </svg>
          {pose.view_count}
        </div>
      </div>
      
      {/* 标题和描述 */}
      <div className="p-3">
        <h3 className="font-medium text-gray-900 line-clamp-1">{pose.title}</h3>
        {pose.description && (
          <p className="mt-1 text-sm text-gray-500 line-clamp-2">{pose.description}</p>
        )}
      </div>
    </div>
  );
}
