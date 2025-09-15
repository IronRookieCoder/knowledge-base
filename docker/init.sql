-- 数据库初始化脚本
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建索引以提高查询性能
-- 这些索引将在应用启动时通过SQLAlchemy自动创建，这里提供备用方案

-- 为文档表创建额外的索引
-- CREATE INDEX IF NOT EXISTS idx_documents_source_type_category ON documents(source_type, category);
-- CREATE INDEX IF NOT EXISTS idx_documents_updated_at_desc ON documents(updated_at DESC);
-- CREATE INDEX IF NOT EXISTS idx_documents_title_gin ON documents USING gin(to_tsvector('english', title));
-- CREATE INDEX IF NOT EXISTS idx_documents_content_gin ON documents USING gin(to_tsvector('english', content));

-- 为同步日志表创建索引
-- CREATE INDEX IF NOT EXISTS idx_sync_logs_created_at_desc ON sync_logs(created_at DESC);
-- CREATE INDEX IF NOT EXISTS idx_sync_logs_source_status ON sync_logs(source_type, status);

-- 设置时区
SET timezone = 'UTC';