// 内容脚本

// 页面状态
let pageState = {
  isBackground: false,
  videoElement: null,
  originalQuality: 'auto',
  playbackTime: 0,
  danmakuState: true,
  animationState: true,
  wasPlaying: false,
  originalQualityText: null,
  originalStyle: null,
  originalPlayerBg: null,
  canvasStates: null
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
async function switchToBackground() {
  if (!pageState.videoElement) return;

  console.log('省流模式：窗口最小化，开始切换低画质');

  // 1. 保存当前播放状态
  pageState.wasPlaying = !pageState.videoElement.paused;
  pageState.playbackTime = pageState.videoElement.currentTime;

  // 2. 【核心】切换到最低画质 (省流量大头)
  // 低画质(360P)通常只有几百KB/秒，比高清省90%以上
  await switchToLowQuality();

  // 3. 【核心】开启"听歌模式"
  // 视频继续播放(保持下载和音频)，但把画面移出屏幕
  if (pageState.wasPlaying) {
    enableAudioOnlyMode();
  }

  // 4. 清理页面干扰
  hideDanmaku();
  disableAnimations();
}

// 切换到前台模式
function switchToForeground() {
  console.log('省流模式：窗口恢复，开始恢复画质');

  // 1. 关闭"听歌模式"，恢复画面显示
  disableAudioOnlyMode();

  // 2. 恢复原来的画质
  restoreQuality();

  // 3. 恢复弹幕和动画
  restoreDanmaku();
  restoreAnimations();
}

// ==========================================
// 核心功能函数
// ==========================================

// 切换到最低画质
async function switchToLowQuality() {
  const qualityBtn = document.querySelector('.bpx-player-ctrl-quality-result');
  if (!qualityBtn) {
    console.log('省流模式：找不到画质按钮');
    return;
  }

  // 点击打开画质列表
  qualityBtn.click();
  await sleep(300);

  // 等待菜单完全展开
  await waitForElement('.bpx-player-ctrl-quality-menu-item', 1000);

  // 直接点击倒数第二个按钮（你的发现！）
  const qualityItems = document.querySelectorAll('.bpx-player-ctrl-quality-menu-item');
  if (qualityItems.length >= 2) {
    const targetItem = qualityItems[qualityItems.length - 2];
    console.log('省流模式：切换到最低画质', targetItem.textContent.trim());
    targetItem.click();
  } else {
    console.log('省流模式：画质选项不足，无法切换');
  }
}

// 恢复画质
async function restoreQuality() {
  // 如果之前没保存画质信息，就不操作
  if (!pageState.originalQualityText) return;

  const qualityBtn = document.querySelector('.bpx-player-ctrl-quality-result');
  if (!qualityBtn) return;

  // 如果当前画质已经是原来的画质（用户手动切回来了，或者没变），就不操作
  if (qualityBtn.textContent.trim() === pageState.originalQualityText) return;

  // 打开菜单
  qualityBtn.click();
  await sleep(300);

  // 遍历找到原来的画质选项并点击
  const qualityItems = document.querySelectorAll(`
    .bpx-player-ctrl-quality-menu-item,
    [class*="quality-menu-item"]
  `);
  
  for (const item of qualityItems) {
    if (item.textContent.trim() === pageState.originalQualityText) {
      console.log('省流模式：恢复画质到', pageState.originalQualityText);
      item.click();
      break;
    }
  }
}

// 开启听歌模式（画面隐藏，声音继续）
function enableAudioOnlyMode() {
  const video = pageState.videoElement;
  if (!video) return;

  // 保存原始样式，以便恢复
  pageState.originalStyle = video.style.cssText;

  // 关键Hack：
  // 1. 确保没有暂停
  if (video.paused) video.play();
  
  // 2. 把视频移出视口
  video.style.position = 'fixed';
  video.style.top = '-9999px';
  video.style.left = '-9999px';
  video.style.width = '1px';
  video.style.height = '1px';
  video.style.opacity = '0';

  // 3. 把播放器区域涂黑，假装视频暂停了
  const playerWrap = document.querySelector('.bilibili-player-video-wrap') || 
                     document.querySelector('#bilibili-player');
  if (playerWrap) {
    pageState.originalPlayerBg = playerWrap.style.background;
    playerWrap.style.background = '#000';
  }
}

// 关闭听歌模式（恢复画面）
function disableAudioOnlyMode() {
  const video = pageState.videoElement;
  if (!video) return;

  // 恢复视频样式
  if (pageState.originalStyle) {
    video.style.cssText = pageState.originalStyle;
  } else {
    video.style.position = '';
    video.style.top = '';
    video.style.left = '';
    video.style.width = '';
    video.style.height = '';
    video.style.opacity = '';
  }

  // 恢复播放器背景
  const playerWrap = document.querySelector('.bilibili-player-video-wrap') || 
                     document.querySelector('#bilibili-player');
  if (playerWrap && pageState.originalPlayerBg !== undefined) {
    playerWrap.style.background = pageState.originalPlayerBg;
  }
}

// 辅助函数：延时
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// 辅助函数：等待元素出现
function waitForElement(selector, timeout = 500) {
  return new Promise((resolve) => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const element = document.querySelector(selector);
      if (element) {
        clearInterval(interval);
        resolve(element);
      } else if (Date.now() - startTime > timeout) {
        clearInterval(interval);
        resolve(null);
      }
    }, 50);
  });
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