// Popup脚本

// DOM元素
const elements = {
  statusIcon: document.getElementById('statusIcon'),
  statusText: document.getElementById('statusText'),
  modeValue: document.getElementById('modeValue'),
  savedTraffic: document.getElementById('savedTraffic'),
  progressCircle: document.getElementById('progressCircle'),
  downloadSpeed: document.getElementById('downloadSpeed'),
  sessionTraffic: document.getElementById('sessionTraffic'),
  totalTraffic: document.getElementById('totalTraffic'),
  smartSaveToggle: document.getElementById('smartSaveToggle'),
  cleanupToggle: document.getElementById('cleanupToggle'),
  trafficToggle: document.getElementById('trafficToggle'),
  logsHeader: document.getElementById('logsHeader'),
  expandIcon: document.getElementById('expandIcon'),
  logsContent: document.getElementById('logsContent'),
  logList: document.getElementById('logList')
};

// 流量数据
let trafficData = {
  totalBytes: 0,
  totalSavedBytes: 0,
  sessions: []
};

// 实时速率模拟
let speed = 0;
let speedInterval;

// 初始化
async function init() {
  // 获取流量数据
  await fetchTrafficData();
  
  // 更新UI
  updateUI();
  
  // 开始实时速率模拟
  startSpeedSimulation();
  
  // 绑定事件
  bindEvents();
  
  // 定期更新数据
  setInterval(fetchTrafficData, 5000);
}

// 获取流量数据
async function fetchTrafficData() {
  try {
    const response = await chrome.runtime.sendMessage({ action: 'getTrafficData' });
    if (response) {
      trafficData = response;
      updateUI();
    }
  } catch (e) {
    console.error('获取流量数据失败:', e);
  }
}

// 更新UI
function updateUI() {
  // 更新节省流量
  const savedMB = (trafficData.totalSavedBytes / (1024 * 1024)).toFixed(2);
  elements.savedTraffic.textContent = `${savedMB} MB`;
  
  // 更新进度环
  const totalMB = (trafficData.totalBytes / (1024 * 1024)).toFixed(2);
  const progress = totalMB > 0 ? (trafficData.totalSavedBytes / trafficData.totalBytes) * 100 : 0;
  const circumference = 2 * Math.PI * 50;
  const offset = circumference - (progress / 100) * circumference;
  elements.progressCircle.style.strokeDashoffset = offset;
  
  // 更新会话和总计流量
  elements.sessionTraffic.textContent = `${totalMB} MB`;
  elements.totalTraffic.textContent = `${totalMB} MB`;
  
  // 更新日志
  updateLogs();
}

// 更新日志
function updateLogs() {
  elements.logList.innerHTML = '';
  
  // 显示最近5条记录
  const recentSessions = trafficData.sessions.slice(-5).reverse();
  
  recentSessions.forEach(session => {
    const logItem = createLogItem(session);
    elements.logList.appendChild(logItem);
  });
  
  if (recentSessions.length === 0) {
    const emptyLog = document.createElement('div');
    emptyLog.className = 'log-item';
    emptyLog.textContent = '暂无数据';
    elements.logList.appendChild(emptyLog);
  }
}

// 创建日志项
function createLogItem(session) {
  const logItem = document.createElement('div');
  logItem.className = 'log-item';
  
  const time = new Date(session.timestamp).toLocaleTimeString();
  const site = new URL(session.url).hostname;
  const traffic = (session.bytes / (1024 * 1024)).toFixed(2);
  const saved = (session.savedBytes / (1024 * 1024)).toFixed(2);
  
  logItem.innerHTML = `
    <div class="log-time">${time}</div>
    <div class="log-site">${site}</div>
    <div class="log-traffic">${traffic} MB</div>
    <div class="log-saved">节省: ${saved} MB</div>
  `;
  
  return logItem;
}

// 开始实时速率模拟
function startSpeedSimulation() {
  speedInterval = setInterval(() => {
    // 模拟速率变化
    speed = Math.max(0, speed + (Math.random() - 0.5) * 100);
    
    // 更新速率显示
    if (speed < 1024) {
      elements.downloadSpeed.textContent = `${speed.toFixed(0)} KB/s`;
    } else {
      elements.downloadSpeed.textContent = `${(speed / 1024).toFixed(2)} MB/s`;
    }
  }, 1000);
}

// 绑定事件
function bindEvents() {
  // 日志展开/收起
  elements.logsHeader.addEventListener('click', () => {
    elements.logsContent.classList.toggle('expanded');
    elements.expandIcon.classList.toggle('expanded');
  });
  
  // 功能开关
  elements.smartSaveToggle.addEventListener('change', (e) => {
    // 保存设置
    chrome.storage.local.set({ smartSaveEnabled: e.target.checked });
  });
  
  elements.cleanupToggle.addEventListener('change', (e) => {
    chrome.storage.local.set({ cleanupEnabled: e.target.checked });
  });
  
  elements.trafficToggle.addEventListener('change', (e) => {
    chrome.storage.local.set({ trafficEnabled: e.target.checked });
  });
  
  // 获取当前标签页状态
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.runtime.sendMessage({ action: 'getTabState' }, (response) => {
        if (response) {
          updateTabStatus(response);
        }
      });
    }
  });
}

// 更新标签页状态
function updateTabStatus(state) {
  if (state.isBackground) {
    elements.statusIcon.textContent = '🌙';
    elements.statusText.textContent = '后台省流中';
    elements.modeValue.textContent = '纯音频';
  } else {
    elements.statusIcon.textContent = '🟢';
    elements.statusText.textContent = '前台播放中';
    elements.modeValue.textContent = '全画质';
  }
}

// 清理
function cleanup() {
  if (speedInterval) {
    clearInterval(speedInterval);
  }
}

// 初始化
init();

// 页面卸载时清理
window.addEventListener('unload', cleanup);