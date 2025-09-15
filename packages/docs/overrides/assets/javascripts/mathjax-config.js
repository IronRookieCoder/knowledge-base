// MathJax 配置 - 适用于内网环境
// 如需在完全离线环境使用，请下载 MathJax 库到本地

window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]], 
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  },
  loader: {
    load: ['[tex]/ams']
  },
  startup: {
    pageReady: () => {
      return MathJax.startup.defaultPageReady();
    }
  }
};

// 动态加载 MathJax（可选，如果需要数学公式支持）
// 在内网环境中，建议下载 MathJax 到本地服务器
(function() {
  // 检查是否需要加载 MathJax
  if (document.querySelector('.arithmatex')) {
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js';
    script.async = true;
    script.onerror = function() {
      console.warn('MathJax CDN 加载失败，如需数学公式支持请配置本地 MathJax');
    };
    document.head.appendChild(script);
  }
})();