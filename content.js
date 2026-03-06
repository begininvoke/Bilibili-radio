// 内容脚本

// 页面状态
let pageState = {
  isBackground: false,
  videoElement: null,
  originalQuality: 'auto',
  playbackTime: 0,
  danmakuState: true,
  animationState: true,
  wasPlaying: false
};

// 初始化
function init() {
  // 查找视频元素
  findVideoElement();
  
  // 监听标签页可见性变化
  document.addEventListener('visibilitychange', handleVisibilityChange);
  
  // 监听视频播放状态
  if (pageState.videoElement) {
    pageState.videoElement.addEventListener('timeupdate', handleTimeUpdate);
  }
  
  // 监听来自后台的消息
  chrome.runtime.onMessage.addListener(handleMessage);
  
  // 初始化弹幕状态
  saveDanmakuState();
}

// 查找视频元素
function findVideoElement() {
  // 查找常见的视频元素
  pageState.videoElement = document.querySelector('video');
  
  // 如果没找到，尝试在iframe中查找
  if (!pageState.videoElement) {
    const iframes = document.querySelectorAll('iframe');
    for (const iframe of iframes) {
      try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        pageState.videoElement = iframeDoc.querySelector('video');
        if (pageState.videoElement) break;
      } catch (e) {
        // 跨域iframe无法访问
      }
    }
  }
}

// 处理标签页可见性变化
function handleVisibilityChange() {
  const isBackground = document.hidden;
  pageState.isBackground = isBackground;
  
  // 通知后台脚本
  chrome.runtime.sendMessage({ 
    action: 'tabVisibilityChanged', 
    isBackground: isBackground 
  });
  
  // 切换模式
  if (isBackground) {
    switchToBackground();
  } else {
    switchToForeground();
  }
}

// 处理视频时间更新
function handleTimeUpdate() {
  if (pageState.videoElement) {
    pageState.playbackTime = pageState.videoElement.currentTime;
  }
}

// 处理来自后台的消息
function handleMessage(message) {
  switch (message.action) {
    case 'switchToBackground':
      switchToBackground();
      break;
    case 'switchToForeground':
      switchToForeground();
      break;
    case 'windowMinimized':
      // 窗口最小化时，强制切换到后台模式
      if (!pageState.isBackground) {
        pageState.isBackground = true;
        switchToBackground();
      }
      break;
    case 'windowRestored':
      // 窗口恢复时，切换到前台模式
      if (pageState.isBackground) {
        pageState.isBackground = false;
        switchToForeground();
      }
      break;
  }
}

// 切换到后台模式
function switchToBackground() {
  // 记录当前状态
  if (pageState.videoElement) {
    pageState.playbackTime = pageState.videoElement.currentTime;
    pageState.wasPlaying = !pageState.videoElement.paused;
    
    // 暂停视频播放，这是唯一能有效截断视频流下载的方法
    if (!pageState.videoElement.paused) {
      pageState.videoElement.pause();
    }
  }
  
  // 隐藏弹幕
  hideDanmaku();
  
  // 禁用动画
  disableAnimations();
}

// 切换到前台模式
function switchToForeground() {
  // 恢复弹幕
  restoreDanmaku();
  
  // 恢复动画
  restoreAnimations();
  
  // 恢复视频播放
  if (pageState.videoElement) {
    // 恢复播放位置
    if (pageState.playbackTime > 0) {
      pageState.videoElement.currentTime = pageState.playbackTime;
    }
    
    // 如果之前在播放，则恢复播放
    if (pageState.wasPlaying) {
      pageState.videoElement.play().catch(e => {
        console.log('恢复播放失败:', e);
      });
    }
  }
}

// 保存弹幕状态
function saveDanmakuState() {
  // B站弹幕
  const bilibiliDanmaku = document.querySelector('.bilibili-player-video-danmaku');
  if (bilibiliDanmaku) {
    pageState.danmakuState = bilibiliDanmaku.style.display !== 'none';
  }
  
  // YouTube弹幕
  const youtubeDanmaku = document.querySelector('.ytp-caption-window-container');
  if (youtubeDanmaku) {
    pageState.danmakuState = youtubeDanmaku.style.display !== 'none';
  }
}

// 隐藏弹幕
function hideDanmaku() {
  // B站弹幕
  const bilibiliDanmaku = document.querySelector('.bilibili-player-video-danmaku');
  if (bilibiliDanmaku) {
    bilibiliDanmaku.style.display = 'none';
  }
  
  // YouTube弹幕
  const youtubeDanmaku = document.querySelector('.ytp-caption-window-container');
  if (youtubeDanmaku) {
    youtubeDanmaku.style.display = 'none';
  }
  
  // 其他网站弹幕
  const danmakuElements = document.querySelectorAll('.danmaku, .comment, .subtitle');
  danmakuElements.forEach(element => {
    element.style.display = 'none';
  });
}

// 恢复弹幕
function restoreDanmaku() {
  if (pageState.danmakuState) {
    // B站弹幕
    const bilibiliDanmaku = document.querySelector('.bilibili-player-video-danmaku');
    if (bilibiliDanmaku) {
      bilibiliDanmaku.style.display = 'block';
    }
    
    // YouTube弹幕
    const youtubeDanmaku = document.querySelector('.ytp-caption-window-container');
    if (youtubeDanmaku) {
      youtubeDanmaku.style.display = 'block';
    }
    
    // 其他网站弹幕
    const danmakuElements = document.querySelectorAll('.danmaku, .comment, .subtitle');
    danmakuElements.forEach(element => {
      element.style.display = 'block';
    });
  }
}

// 禁用动画
function disableAnimations() {
  // 创建样式元素
  const style = document.createElement('style');
  style.id = 'smart-save-traffic-animation-disable';
  style.textContent = `
    * {
      animation: none !important;
      transition: none !important;
    }
    canvas {
      display: none !important;
    }
    img[src*=".gif"] {
      display: none !important;
    }
  `;
  document.head.appendChild(style);
  
  // 暂停Canvas绘制
  const canvases = document.querySelectorAll('canvas');
  canvases.forEach(canvas => {
    const ctx = canvas.getContext('2d');
    if (ctx) {
      // 保存当前状态
      pageState.canvasStates = pageState.canvasStates || new Map();
      pageState.canvasStates.set(canvas, canvas.toDataURL());
    }
  });
}

// 恢复动画
function restoreAnimations() {
  // 移除样式元素
  const style = document.getElementById('smart-save-traffic-animation-disable');
  if (style) {
    style.remove();
  }
  
  // 恢复Canvas
  if (pageState.canvasStates) {
    pageState.canvasStates.forEach((dataUrl, canvas) => {
      const img = new Image();
      img.onload = () => {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(img, 0, 0);
        }
      };
      img.src = dataUrl;
    });
    pageState.canvasStates = null;
  }
}

// 页面加载完成后初始化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// 页面卸载前保存状态
window.addEventListener('beforeunload', () => {
  if (pageState.videoElement) {
    pageState.playbackTime = pageState.videoElement.currentTime;
  }
});