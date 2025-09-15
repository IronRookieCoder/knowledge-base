"""通用工具函数"""

import os
import hashlib
import secrets
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
import unicodedata


def generate_slug(text: str, max_length: int = 100) -> str:
    """生成URL友好的slug"""
    # 转换为小写并移除特殊字符
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text)

    # 截断到指定长度
    if len(text) > max_length:
        text = text[:max_length].rstrip('-')

    return text.strip('-')


def generate_api_key() -> str:
    """生成API密钥"""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """对API密钥进行哈希"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def extract_text_summary(text: str, max_length: int = 200) -> str:
    """提取文本摘要"""
    # 移除多余空白字符
    text = re.sub(r'\s+', ' ', text.strip())

    if len(text) <= max_length:
        return text

    # 截断到最近的句号或换行
    truncated = text[:max_length]
    last_period = truncated.rfind('。')
    last_newline = truncated.rfind('\n')

    if last_period > max_length * 0.7:
        return truncated[:last_period + 1]
    elif last_newline > max_length * 0.7:
        return truncated[:last_newline]
    else:
        return truncated + '...'


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)

    # 移除开头和结尾的点和空格
    filename = filename.strip('. ')

    return filename


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """提取关键词（简单实现）"""
    # 移除标点符号并转为小写
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text.lower())

    # 分词（简单按空格分割，实际使用时建议用jieba）
    words = text.split()

    # 过滤短词和常见词
    stop_words = {'的', '是', '在', '和', '与', '或', '但', '如果', '因为', '所以',
                  'the', 'is', 'in', 'and', 'or', 'but', 'if', 'because', 'so'}

    keywords = [word for word in words
                if len(word) > 1 and word not in stop_words]

    # 统计词频并返回最常见的词
    word_count = {}
    for word in keywords:
        word_count[word] = word_count.get(word, 0) + 1

    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:max_keywords]]


def parse_file_path(file_path: str) -> Dict[str, str]:
    """解析文件路径信息"""
    path = Path(file_path)
    return {
        'directory': str(path.parent),
        'filename': path.name,
        'stem': path.stem,
        'suffix': path.suffix,
        'absolute_path': str(path.resolve()),
    }


def ensure_directory(directory: Union[str, Path]) -> None:
    """确保目录存在"""
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_file_hash(file_path: Union[str, Path]) -> str:
    """计算文件MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1

    return f"{size_bytes:.1f}{size_names[i]}"


def parse_git_url(url: str) -> Dict[str, Optional[str]]:
    """解析Git URL"""
    parsed = urlparse(url)

    # 处理SSH格式的Git URL (git@host:owner/repo.git)
    if parsed.scheme == '' and '@' in url:
        parts = url.split('@')[1].split(':')
        if len(parts) == 2:
            host = parts[0]
            path = parts[1]
            return {
                'host': host,
                'owner': path.split('/')[0] if '/' in path else None,
                'repo': path.split('/')[-1].replace('.git', '') if '/' in path else None,
                'protocol': 'ssh'
            }

    # 处理HTTPS格式的Git URL
    if parsed.scheme in ['http', 'https']:
        path_parts = parsed.path.strip('/').split('/')
        return {
            'host': parsed.hostname,
            'owner': path_parts[0] if len(path_parts) > 0 else None,
            'repo': path_parts[1].replace('.git', '') if len(path_parts) > 1 else None,
            'protocol': parsed.scheme
        }

    return {'host': None, 'owner': None, 'repo': None, 'protocol': None}


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def now_utc() -> datetime:
    """获取当前UTC时间"""
    return datetime.now(timezone.utc)


def format_duration(seconds: float) -> str:
    """格式化时间间隔"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        return f"{seconds/60:.1f}分钟"
    else:
        return f"{seconds/3600:.1f}小时"


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """深度合并字典"""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix