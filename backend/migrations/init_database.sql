-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS pose_gallery DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE pose_gallery;

-- 删除已存在的表（开发环境使用，生产环境请谨慎）
DROP TABLE IF EXISTS pose_tags;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS search_history;
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
    ai_tags TEXT COMMENT 'AI标签，逗号分隔（冗余字段，便于快速搜索）',
    
    -- AI分析相关字段
    ai_analyzed_at TIMESTAMP NULL COMMENT 'AI分析完成时间',
    ai_confidence DECIMAL(3,2) DEFAULT 0.90 COMMENT 'AI分析置信度',
    processing_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending' COMMENT '处理状态',
    error_message TEXT COMMENT '处理错误信息',
    
    -- 统计字段
    view_count INT DEFAULT 0 COMMENT '浏览次数',
    search_count INT DEFAULT 0 COMMENT '搜索命中次数',
    
    -- 时间字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 状态字段
    status ENUM('pending', 'active', 'hidden') DEFAULT 'active' COMMENT '状态',
    
    -- 基础索引
    INDEX idx_category (scene_category),
    INDEX idx_angle (angle),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_ai_analyzed (ai_analyzed_at),
    INDEX idx_processing_status (processing_status),
    INDEX idx_scene_angle (scene_category, angle),
    INDEX idx_status_category (status, scene_category),
    
    -- 全文搜索索引
    FULLTEXT idx_fulltext (title, description, ai_tags) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='姿势图片表';

-- 创建标签表
CREATE TABLE tags (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL COMMENT '标签名称',
    category ENUM('scene', 'mood', 'pose', 'prop', 'style', 'angle', 'lighting', 'other') DEFAULT 'other' COMMENT '标签分类',
    usage_count INT DEFAULT 0 COMMENT '使用次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_name (name),
    INDEX idx_category (category),
    INDEX idx_usage_count (usage_count),
    FULLTEXT idx_name_fulltext (name) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='标签表';

-- 创建图片标签关联表
CREATE TABLE pose_tags (
    pose_id INT NOT NULL,
    tag_id INT NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.00 COMMENT '标签相关度',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (pose_id, tag_id),
    FOREIGN KEY (pose_id) REFERENCES poses(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    INDEX idx_confidence (confidence)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='图片标签关联表';

-- 创建搜索历史表
CREATE TABLE search_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    query VARCHAR(200) NOT NULL COMMENT '搜索词',
    normalized_query VARCHAR(200) COMMENT '标准化搜索词',
    results_count INT DEFAULT 0 COMMENT '结果数量',
    response_time_ms INT COMMENT '响应时间(毫秒)',
    filter_category VARCHAR(50) COMMENT '筛选分类',
    user_ip VARCHAR(45) COMMENT '用户IP',
    user_agent TEXT COMMENT '用户代理',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_query (query),
    INDEX idx_normalized_query (normalized_query),
    INDEX idx_created_at (created_at),
    INDEX idx_query_time (query, created_at),
    FULLTEXT idx_query_fulltext (query, normalized_query) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='搜索历史表';

-- 创建同义词表（用于搜索扩展）
CREATE TABLE synonyms (
    id INT PRIMARY KEY AUTO_INCREMENT,
    word VARCHAR(100) NOT NULL COMMENT '原词',
    synonym VARCHAR(100) NOT NULL COMMENT '同义词',
    weight DECIMAL(3,2) DEFAULT 1.00 COMMENT '权重',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_synonym (word, synonym),
    INDEX idx_word (word),
    INDEX idx_synonym (synonym)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='同义词表';

-- 插入一些基础同义词数据
INSERT INTO synonyms (word, synonym, weight) VALUES
('写真', '拍照', 0.9),
('写真', '摄影', 0.9),
('美女', '女生', 0.8),
('美女', '女孩', 0.8),
('室内', '屋内', 0.9),
('户外', '室外', 0.9),
('咖啡厅', '咖啡馆', 1.0),
('坐姿', '坐着', 0.9),
('站姿', '站着', 0.9),
('躺姿', '躺着', 0.9);

-- 创建视图：带标签的pose信息
CREATE VIEW pose_with_tags AS
SELECT 
    p.*,
    GROUP_CONCAT(t.name ORDER BY pt.confidence DESC SEPARATOR ',') as tag_names,
    COUNT(t.id) as tag_count
FROM poses p
LEFT JOIN pose_tags pt ON p.id = pt.pose_id
LEFT JOIN tags t ON pt.tag_id = t.id
WHERE p.status = 'active'
GROUP BY p.id;