'use client';

import { useState, useEffect } from 'react';
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
        <button
          onClick={onClose}
          className="absolute -top-10 right-0 text-white hover:text-gray-300 text-xl z-10"
        >
          ✕ 关闭
        </button>

        <div className="bg-white rounded-lg overflow-hidden shadow-2xl flex flex-col lg:flex-row max-h-[80vh]">
          {/* 图片区域 */}
          <div className="lg:w-2/3 relative bg-gray-100 flex items-center justify-center min-h-[300px]">
            <Image
              src={imageError ? '/placeholder.svg' : pose.oss_url}
              alt={pose.title}
              width={800}
              height={600}
              className="max-w-full max-h-full object-contain"
              onError={() => setImageError(true)}
            />
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

            {/* 修复注释问题 - 将注释放在大括号内 */}
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
                <span>浏览: {pose.view_count || 0}</span>
                <span>
                  {pose.created_at && new Date(pose.created_at).toLocaleDateString('zh-CN')}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}