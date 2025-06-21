'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { Pose } from '@/lib/types';

interface ImageModalProps {
  pose: Pose;
  onClose: () => void;
}

export default function ImageModal({ pose, onClose }: ImageModalProps) {
  const [imageError, setImageError] = useState(false);

  // ESC键关闭
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  // 防止背景滚动
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-90"
      onClick={onClose}
    >
      <div
        className="relative max-w-7xl max-h-[90vh] mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          className="absolute -top-12 right-0 text-white hover:text-gray-300 transition-colors"
        >
          <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div className="bg-white rounded-lg overflow-hidden flex flex-col lg:flex-row">
          {/* 图片区域 */}
          <div className="relative lg:w-2/3 bg-gray-100">
            <div className="relative aspect-[3/4] lg:aspect-auto lg:h-[80vh]">
              <Image
                src={imageError ? '/placeholder.svg' : pose.oss_url}
                alt={pose.title}
                fill
                className="object-contain"
                onError={() => setImageError(true)}
                priority
              />
            </div>
          </div>

          {/* 信息区域 */}
          <div className="lg:w-1/3 p-6 overflow-y-auto max-h-[80vh]">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">{pose.title}</h2>
            
            {pose.description && (
              <div className="mb-6">
                <h3 className="text-sm font-medium text-gray-500 mb-2">描述</h3>
                <p className="text-gray-700">{pose.description}</p>
              </div>
            )}

            {pose.scene_category && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-2">场景</h3>
                <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                  {pose.scene_category}
                </span>
              </div>
            )}

            {pose.angle && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-2">拍摄角度</h3>
                <p className="text-gray-700">{pose.angle}</p>
              </div>
            )}

            {pose.props && pose.props.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-2">道具</h3>
                <div className="flex flex-wrap gap-2">
                  {pose.props.map((prop, index) => (
                    <span key={index} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm">
                      {prop}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {pose.shooting_tips && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-2">拍摄建议</h3>
                <p className="text-gray-700 bg-yellow-50 p-3 rounded-lg text-sm">
                  💡 {pose.shooting_tips}
                </p>
              </div>
            )}

// components/ImageModal.tsx (继续)
            {pose.ai_tags && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-500 mb-2">标签</h3>
                <div className="flex flex-wrap gap-1">
                  {pose.ai_tags.split(',').map((tag, index) => (
                    <span key={index} className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                      #{tag.trim()}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-6 pt-6 border-t border-gray-200">
              <div className="flex items-center justify-between text-sm text-gray-500">
                <span>浏览次数：{pose.view_count}</span>
                <span>{new Date(pose.created_at).toLocaleDateString('zh-CN')}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
