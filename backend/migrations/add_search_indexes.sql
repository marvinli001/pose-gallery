-- 添加全文索引
ALTER TABLE poses ADD FULLTEXT(title, description, ai_tags);

-- 添加复合索引提高筛选性能
CREATE INDEX idx_poses_category_angle ON poses(scene_category, angle);
CREATE INDEX idx_poses_status_created ON poses(status, created_at);
CREATE INDEX idx_poses_view_count ON poses(view_count DESC);

-- 标签搜索优化
CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_pose_tags_pose_tag ON pose_tags(pose_id, tag_id);

-- 搜索历史分析索引
CREATE INDEX idx_search_history_query ON search_history(normalized_query);
CREATE INDEX idx_search_history_created ON search_history(created_at);