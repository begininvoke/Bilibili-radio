// 后台服务脚本

// 存储标签页状态
const tabStates = new Map();

// 存储流量数据
let trafficData = {
  totalBytes: 0,
  totalSavedBytes: 0,
  sessions: []
};

// 当前窗口状态
let currentWindowId = null;
let isWindowMinimized = false;

// 初始化流量数据
async function initTrafficData() {
  const data = await chrome.storage.local.get(['trafficData']);
  if (data.trafficData) {
    trafficData = data.trafficData;
  }
}

// 保存流量数据
async function saveTrafficData() {
  await chrome.storage.local.set({ trafficData });
}

// 处理标签页可见性变化
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    // 检查是否是视频网站
    if (isVideoSite(tab.url)) {
      tabStates.set(tabId, {
        url: tab.url,
        isBackground: false,
        lastActivity: Date.now(),
        quality: 'auto',
        playbackTime: 0
      });
    }
  }
});

// 处理标签页激活状态变化
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  // 标记所有标签页为后台
  for (const [tabId, state] of tabStates.entries()) {
    if (tabId !== activeInfo.tabId) {
      state.isBackground = true;
      state.lastActivity = Date.now();
    } else {
      state.isBackground = false;
      // 通知内容脚本恢复前台模式
      try {
        await chrome.tabs.sendMessage(tabId, { action: 'switchToForeground' });
      } catch (e) {
        // 内容脚本可能还未加载
      }
    }
  }
});

// 处理标签页关闭
chrome.tabs.onRemoved.addListener((tabId) => {
  tabStates.delete(tabId);
});

// 监听窗口焦点变化
chrome.windows.onFocusChanged.addListener(async (windowId) => {
  // windowId为-1表示没有窗口获得焦点（最小化或切换到其他应用）
  if (windowId === chrome.windows.WINDOW_ID_NONE) {
    // 窗口最小化或失去焦点
    isWindowMinimized = true;
    
    // 通知所有视频标签页切换到后台模式
    for (const [tabId, state] of tabStates.entries()) {
      if (!state.isBackground) {
        state.isBackground = true;
        state.lastActivity = Date.now();
        
        try {
          await chrome.tabs.sendMessage(tabId, { action: 'windowMinimized' });
        } catch (e) {
          // 内容脚本可能还未加载
        }
      }
    }
  } else {
    // 窗口恢复焦点
    isWindowMinimized = false;
    currentWindowId = windowId;
    
    // 获取当前窗口的活动标签页
    try {
      const tabs = await chrome.tabs.query({ active: true, windowId: windowId });
      if (tabs.length > 0) {
        const activeTab = tabs[0];
        const state = tabStates.get(activeTab.id);
        
        if (state && state.isBackground) {
          state.isBackground = false;
          
          try {
            await chrome.tabs.sendMessage(activeTab.id, { action: 'windowRestored' });
          } catch (e) {
            // 内容脚本可能还未加载
          }
        }
      }
    } catch (e) {
      console.error('获取活动标签页失败:', e);
    }
  }
});

// 检查是否是视频网站
function isVideoSite(url) {
  const videoSites = [
    'bilibili.com',
    'youtube.com'
  ];
  return videoSites.some(site => url.includes(site));
}

// 视频源拦截与修改
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    const tabId = details.tabId;
    if (tabId === -1) return; // 非标签页请求

    const state = tabStates.get(tabId);
    if (!state || !state.isBackground) return; // 不在后台或不是视频网站

    const url = details.url;

    // B站适配
    if (url.includes('bilibili.com') && url.includes('fnval')) {
      // 修改fnval参数，强制请求仅音频流
      const newUrl = url.replace(/fnval=\d+/, 'fnval=16');
      return { redirectUrl: newUrl };
    }

    // YouTube适配
    if (url.includes('googlevideo.com') && url.includes('itag=')) {
      // 修改itag参数，使用仅音频的itag值
      // 140: AAC audio 128kbps
      const newUrl = url.replace(/itag=\d+/, 'itag=140');
      return { redirectUrl: newUrl };
    }

  },
  {
    urls: [
      '*://*.bilibili.com/*',
      '*://*.googlevideo.com/*'
    ]
  },
  ['blocking']
);

// 流量监控
chrome.webRequest.onCompleted.addListener(
  (details) => {
    const tabId = details.tabId;
    if (tabId === -1) return; // 非标签页请求

    const state = tabStates.get(tabId);
    if (!state) return;

    const url = details.url;
    // 筛选视频流请求
    if (isVideoRequest(url, details.type)) {
      const contentLength = getContentLength(details.responseHeaders);
      if (contentLength > 0) {
        // 计算节省的流量（假设纯音频流量是视频流量的10%）
        const savedBytes = state.isBackground ? contentLength * 0.9 : 0;
        
        // 更新流量数据
        trafficData.totalBytes += contentLength;
        trafficData.totalSavedBytes += savedBytes;
        
        // 添加会话记录
        trafficData.sessions.push({
          url: state.url,
          bytes: contentLength,
          savedBytes: savedBytes,
          timestamp: Date.now(),
          duration: 0 // 后续可通过其他方式计算
        });
        
        // 限制会话记录数量
        if (trafficData.sessions.length > 100) {
          trafficData.sessions = trafficData.sessions.slice(-100);
        }
        
        // 保存流量数据
        saveTrafficData();
      }
    }
  },
  {
    urls: ['<all_urls>']
  },
  ['responseHeaders']
);

// 检查是否是视频请求
function isVideoRequest(url, type) {
  const videoExtensions = ['.m4s', '.mp4', '.m3u8', '.mpd'];
  const videoTypes = ['media'];
  
  return videoTypes.includes(type) || 
    videoExtensions.some(ext => url.includes(ext));
}

// 获取内容长度
function getContentLength(headers) {
  if (!headers) return 0;
  
  const contentLengthHeader = headers.find(header => 
    header.name.toLowerCase() === 'content-length'
  );
  
  if (contentLengthHeader) {
    return parseInt(contentLengthHeader.value) || 0;
  }
  
  // 使用encodedDataLength作为备选
  return 0;
}

// 处理来自内容脚本的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const tabId = sender.tab?.id;
  if (!tabId) return;

  switch (message.action) {
    case 'tabVisibilityChanged':
      const state = tabStates.get(tabId);
      if (state) {
        state.isBackground = message.isBackground;
        state.lastActivity = Date.now();
        
        // 通知内容脚本切换模式
        if (message.isBackground) {
          chrome.tabs.sendMessage(tabId, { action: 'switchToBackground' });
        } else {
          chrome.tabs.sendMessage(tabId, { action: 'switchToForeground' });
        }
      }
      break;
    
    case 'getTrafficData':
      sendResponse(trafficData);
      break;
    
    case 'getTabState':
      sendResponse(tabStates.get(tabId));
      break;
    
    case 'getWindowState':
      sendResponse({
        isWindowMinimized: isWindowMinimized,
        currentWindowId: currentWindowId
      });
      break;
  }
});

// 初始化
initTrafficData();

// 定期清理过期的会话记录
setInterval(() => {
  const oneWeekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  trafficData.sessions = trafficData.sessions.filter(session => 
    session.timestamp > oneWeekAgo
  );
  saveTrafficData();
}, 24 * 60 * 60 * 1000); // 每天清理一次