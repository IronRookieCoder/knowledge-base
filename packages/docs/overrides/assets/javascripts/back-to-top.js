/**
 * 回到顶部功能 JavaScript
 * AI-Native 开发实践指南
 */

(function() {
    'use strict';
    
    // 配置选项
    const config = {
        showOffset: 300,           // 滚动多少像素后显示按钮
        scrollDuration: 800,       // 回到顶部动画持续时间(ms)
        showProgressRing: true,    // 是否显示进度环
        buttonText: '↑',           // 按钮文本
        ariaLabel: '回到顶部'      // 无障碍标签
    };
    
    let backToTopButton = null;
    let progressRing = null;
    let progressCircle = null;
    let isScrolling = false;
    let circumference = 0;
    
    /**
     * 创建回到顶部按钮
     */
    function createBackToTopButton() {
        // 创建按钮元素
        backToTopButton = document.createElement('button');
        backToTopButton.className = 'back-to-top';
        backToTopButton.innerHTML = config.buttonText;
        backToTopButton.setAttribute('aria-label', config.ariaLabel);
        backToTopButton.setAttribute('title', config.ariaLabel);
        
        // 添加点击事件
        backToTopButton.addEventListener('click', handleBackToTopClick);
        
        // 如果启用进度环，创建进度环元素
        if (config.showProgressRing) {
            createProgressRing();
        }
        
        // 添加到页面
        document.body.appendChild(backToTopButton);
        if (progressRing) {
            document.body.appendChild(progressRing);
        }
    }
    
    /**
     * 创建进度环
     */
    function createProgressRing() {
        progressRing = document.createElement('div');
        progressRing.className = 'back-to-top-progress';
        
        const radius = 20;
        circumference = 2 * Math.PI * radius;
        
        progressRing.innerHTML = `
            <svg viewBox="0 0 50 50">
                <circle class="progress-ring-bg" cx="25" cy="25" r="${radius}"></circle>
                <circle class="progress-ring" cx="25" cy="25" r="${radius}"
                        style="stroke-dasharray: ${circumference}; stroke-dashoffset: ${circumference}">
                </circle>
            </svg>
        `;
        
        progressCircle = progressRing.querySelector('.progress-ring');
    }
    
    /**
     * 处理回到顶部按钮点击
     */
    function handleBackToTopClick(e) {
        e.preventDefault();
        
        // 添加点击动画
        backToTopButton.classList.add('clicked');
        setTimeout(() => {
            backToTopButton.classList.remove('clicked');
        }, 300);
        
        // 平滑滚动到顶部
        scrollToTop();
    }
    
    /**
     * 平滑滚动到顶部
     */
    function scrollToTop() {
        if (isScrolling) return;
        
        isScrolling = true;
        const startPosition = window.pageYOffset;
        const startTime = performance.now();
        
        function scrollAnimation(currentTime) {
            const elapsedTime = currentTime - startTime;
            const progress = Math.min(elapsedTime / config.scrollDuration, 1);
            
            // 使用缓动函数
            const easeInOutQuad = progress < 0.5 
                ? 2 * progress * progress 
                : 1 - Math.pow(-2 * progress + 2, 2) / 2;
            
            window.scrollTo(0, startPosition * (1 - easeInOutQuad));
            
            if (progress < 1) {
                requestAnimationFrame(scrollAnimation);
            } else {
                isScrolling = false;
            }
        }
        
        requestAnimationFrame(scrollAnimation);
    }
    
    /**
     * 更新按钮显示状态和进度
     */
    function updateButtonState() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;
        
        // 计算滚动进度
        const scrollProgress = scrollTop / (documentHeight - windowHeight);
        
        // 显示/隐藏按钮
        if (scrollTop > config.showOffset) {
            backToTopButton.classList.add('show');
            if (progressRing) {
                progressRing.classList.add('show');
            }
        } else {
            backToTopButton.classList.remove('show');
            if (progressRing) {
                progressRing.classList.remove('show');
            }
        }
        
        // 更新进度环
        if (progressCircle && config.showProgressRing) {
            const offset = circumference - (scrollProgress * circumference);
            progressCircle.style.strokeDashoffset = offset;
        }
    }
    
    /**
     * 节流函数
     */
    function throttle(func, delay) {
        let timeoutId;
        let lastExecTime = 0;
        
        return function(...args) {
            const currentTime = Date.now();
            
            if (currentTime - lastExecTime > delay) {
                func.apply(this, args);
                lastExecTime = currentTime;
            } else {
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => {
                    func.apply(this, args);
                    lastExecTime = Date.now();
                }, delay - (currentTime - lastExecTime));
            }
        };
    }
    
    /**
     * 处理键盘事件
     */
    function handleKeydown(e) {
        // 支持键盘导航
        if (e.key === 'Home' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            scrollToTop();
        }
        
        // ESC 键隐藏按钮（如果正在显示工具提示）
        if (e.key === 'Escape' && backToTopButton.classList.contains('show')) {
            backToTopButton.blur();
        }
    }
    
    /**
     * 检测用户偏好设置
     */
    function respectUserPreferences() {
        // 检查用户是否偏好减少动画
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            config.scrollDuration = 0; // 禁用动画
        }
    }
    
    /**
     * 处理页面可见性变化
     */
    function handleVisibilityChange() {
        if (document.hidden) {
            // 页面隐藏时停止滚动动画
            isScrolling = false;
        }
    }
    
    /**
     * 错误处理
     */
    function handleError(error) {
        console.warn('Back to Top: ', error.message);
    }
    
    /**
     * 初始化
     */
    function init() {
        try {
            // 检查环境支持
            if (typeof window === 'undefined' || typeof document === 'undefined') {
                return;
            }
            
            // 尊重用户偏好
            respectUserPreferences();
            
            // 创建按钮
            createBackToTopButton();
            
            // 绑定事件
            const throttledUpdateButtonState = throttle(updateButtonState, 16); // 60fps
            
            window.addEventListener('scroll', throttledUpdateButtonState, { passive: true });
            window.addEventListener('resize', throttledUpdateButtonState, { passive: true });
            window.addEventListener('keydown', handleKeydown);
            document.addEventListener('visibilitychange', handleVisibilityChange);
            
            // 初始状态更新
            updateButtonState();
            
            // 添加加载完成标识
            document.documentElement.setAttribute('data-back-to-top', 'loaded');
            
        } catch (error) {
            handleError(error);
        }
    }
    
    /**
     * 清理函数
     */
    function cleanup() {
        if (backToTopButton) {
            backToTopButton.remove();
        }
        if (progressRing) {
            progressRing.remove();
        }
        
        window.removeEventListener('scroll', updateButtonState);
        window.removeEventListener('resize', updateButtonState);
        window.removeEventListener('keydown', handleKeydown);
        document.removeEventListener('visibilitychange', handleVisibilityChange);
    }
    
    /**
     * 公开API
     */
    window.BackToTop = {
        init: init,
        cleanup: cleanup,
        scrollToTop: scrollToTop,
        config: config
    };
    
    // 自动初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM 已经加载完成
        setTimeout(init, 0);
    }
    
    // 页面卸载时清理
    window.addEventListener('beforeunload', cleanup);
    
})();

/**
 * 扩展功能：支持自定义配置
 * 使用示例：
 * 
 * // 基本使用
 * // 无需额外配置，自动初始化
 * 
 * // 自定义配置
 * window.BackToTop.config.showOffset = 500;
 * window.BackToTop.config.scrollDuration = 1000;
 * window.BackToTop.init(); // 重新初始化
 * 
 * // 手动控制
 * window.BackToTop.scrollToTop(); // 手动触发回到顶部
 */