-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS pose_gallery DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE pose_gallery;

-- 删除已存在的表（开发环境使用，生产环境请谨慎）
DROP TABLE IF EXISTS poses;

-- 创建poses表
CREATE TABLE poses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    oss_key VARCHAR(255) UNIQUE NOT NULL COMMENT 'OSS文件唯一标识',
    oss_url TEXT NOT NULL COMMENT 'OSS完整URL',
    thumbnail_url TEXT COMMENT '缩略图URL',
    title VARCHAR(200) COMMENT '标题',
    description TEXT COMMENT '描述',
    scene_category VARCHAR(50) COMMENT '场景分类',
    angle VARCHAR(50) COMMENT '拍摄角度',
    props JSON COMMENT '道具列表',
    shooting_tips TEXT COMMENT '拍摄建议',
    ai_tags TEXT COMMENT 'AI标签，逗号分隔',
    view_count INT DEFAULT 0 COMMENT '浏览次数',
    search_count INT DEFAULT 0 COMMENT '搜索命中次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    status ENUM('pending', 'active', 'hidden') DEFAULT 'active' COMMENT '状态',
    
    -- 索引
    INDEX idx_category (scene_category),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    FULLTEXT idx_fulltext (title, description, ai_tags) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='姿势图片表';

-- 创建搜索历史表（用于分析，可选）
CREATE TABLE IF NOT EXISTS search_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    query VARCHAR(200) NOT NULL COMMENT '搜索词',
    results_count INT DEFAULT 0 COMMENT '结果数量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_query (query),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='搜索历史表';
