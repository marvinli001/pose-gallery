'use client';

import { useState } from 'react';
import Masonry from 'react-masonry-css';
import { useInView } from 'react-intersection-observer';
import PoseCard from './PoseCard';
import ImageModal from './ImageModal';
import { Pose } from '@/lib/types';

interface PoseGridProps {
  poses: Pose[];
  loading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
}

export default function PoseGrid({ poses, loading, hasMore, onLoadMore }: PoseGridProps) {
  const [selectedPose, setSelectedPose] = useState<Pose | null>(null);
  const { ref, inView } = useInView({
    threshold: 0,
    triggerOnce: false,
  });

  // 加载更多
  if (inView && hasMore && !loading && onLoadMore) {
    onLoadMore();
  }

  // 响应式列数
  const breakpointColumns = {
    default: 4,
    1100: 3,
    700: 2,
    500: 1
  };

  return (
    <>
      <Masonry
        breakpointCols={breakpointColumns}
        className="flex -ml-4 w-auto"
        columnClassName="pl-4 bg-clip-padding"
      >
        {poses.map((pose) => (
          <div key={pose.id} className="mb-4">
            <PoseCard
              pose={pose}
              onClick={() => setSelectedPose(pose)}
            />
          </div>
        ))}
      </Masonry>

      {/* 加载更多触发器 */}
      {hasMore && (
        <div ref={ref} className="flex justify-center py-8">
          {loading && (
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
              <span className="text-gray-500">加载中...</span>
            </div>
          )}
        </div>
      )}

      {/* 空状态 */}
      {!loading && poses.length === 0 && (
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="mt-2 text-gray-500">没有找到相关姿势</p>
        </div>
      )}

      {/* 图片详情弹窗 */}
      {selectedPose && (
        <ImageModal
          pose={selectedPose}
          onClose={() => setSelectedPose(null)}
        />
      )}
    </>
  );
}
