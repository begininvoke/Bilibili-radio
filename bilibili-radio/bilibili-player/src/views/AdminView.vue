<template>
  <div class="admin-page">
    <header class="admin-header">
      <div>
        <div class="title-line">
          <AppIcon name="shield" :size="22" />
          <h1>管理控制台</h1>
        </div>
        <p v-if="summary">数据更新于 {{ formatDateTime(summary.generatedAt) }}</p>
      </div>
      <div class="header-actions">
        <a
          v-if="monitoringUrl"
          class="grafana-link"
          :href="monitoringUrl"
          target="_blank"
          rel="noopener noreferrer"
        >
          <AppIcon name="activity" :size="16" />
          <span>打开 Grafana</span>
          <AppIcon name="external-link" :size="14" />
        </a>
        <button class="refresh-btn" :disabled="isLoading" title="刷新数据" @click="loadAll">
          <AppIcon name="repeat" :size="17" />
        </button>
      </div>
    </header>

    <section v-if="forbidden" class="state-panel">
      <AppIcon name="shield" :size="30" />
      <h2>无权访问管理数据</h2>
      <p>当前会话的管理员权限已失效，请重新登录或联系系统管理员。</p>
      <RouterLink to="/" class="primary-link">返回播放器</RouterLink>
    </section>

    <section v-else-if="loadError && !summary" class="state-panel error-state">
      <AppIcon name="activity" :size="30" />
      <h2>管理数据加载失败</h2>
      <p>{{ loadError }}</p>
      <button class="primary-link" @click="loadAll">重试</button>
    </section>

    <template v-else>
      <div class="range-tabs" role="group" aria-label="统计时间范围">
        <button
          v-for="item in ranges"
          :key="item.value"
          :class="{ active: selectedRange === item.value }"
          @click="selectedRange = item.value"
        >
          {{ item.label }}
        </button>
      </div>

      <section class="metrics-section" aria-labelledby="summary-title">
        <h2 id="summary-title">概览</h2>
        <div class="metric-grid" :aria-busy="isSummaryLoading">
          <article v-for="metric in metrics" :key="metric.label" class="metric-card">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
            <small>{{ metric.note }}</small>
          </article>
        </div>
        <p v-if="loadError" class="inline-error">{{ loadError }}</p>
      </section>

      <section class="users-section" aria-labelledby="users-title">
        <div class="section-heading">
          <div>
            <h2 id="users-title">用户</h2>
            <p>{{ usersPage.total }} 个账户</p>
          </div>
          <span v-if="isUsersLoading" class="loading-label">正在更新</span>
        </div>

        <div class="user-table-wrap">
          <table class="user-table">
            <thead>
              <tr>
                <th>用户</th>
                <th>角色</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>最近登录</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in usersPage.items" :key="user.id">
                <td>
                  <div class="user-cell">
                    <span class="user-initial">{{ user.displayName.slice(0, 1).toUpperCase() || '?' }}</span>
                    <span class="user-copy">
                      <strong>{{ user.displayName }}</strong>
                      <small>{{ user.email || shortId(user.id) }}</small>
                    </span>
                  </div>
                </td>
                <td><span class="role-label" :class="user.role">{{ user.role === 'admin' ? '管理员' : '用户' }}</span></td>
                <td><span class="status-label" :class="user.status">{{ user.status === 'active' ? '正常' : '已停用' }}</span></td>
                <td>{{ formatDate(user.createdAt) }}</td>
                <td>{{ user.lastLoginAt ? formatDateTime(user.lastLoginAt) : '从未登录' }}</td>
              </tr>
              <tr v-if="!isUsersLoading && usersPage.items.length === 0">
                <td colspan="5" class="empty-row">暂无用户数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="totalPages > 1" class="pagination">
          <button :disabled="usersPage.page <= 1 || isUsersLoading" @click="changePage(usersPage.page - 1)">上一页</button>
          <span>第 {{ usersPage.page }} / {{ totalPages }} 页</span>
          <button :disabled="usersPage.page >= totalPages || isUsersLoading" @click="changePage(usersPage.page + 1)">下一页</button>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ApiError, fetchAdminStatsSummary, fetchAdminUsers } from '@/api/client'
import type { AdminStatsSummary, AdminUsersPage } from '@/types'
import AppIcon from '@/components/base/AppIcon.vue'

const PAGE_SIZE = 20
const ranges = [
  { label: '近 7 天', value: '7d' },
  { label: '近 30 天', value: '30d' },
  { label: '近 90 天', value: '90d' },
]

const emptyUsersPage: AdminUsersPage = {
  items: [],
  total: 0,
  page: 1,
  pageSize: PAGE_SIZE,
}

const selectedRange = ref('7d')
const summary = ref<AdminStatsSummary | null>(null)
const usersPage = ref<AdminUsersPage>(emptyUsersPage)
const isSummaryLoading = ref(false)
const isUsersLoading = ref(false)
const forbidden = ref(false)
const loadError = ref<string | null>(null)

const isLoading = computed(() => isSummaryLoading.value || isUsersLoading.value)
const totalPages = computed(() => Math.max(1, Math.ceil(usersPage.value.total / usersPage.value.pageSize)))
const monitoringUrl = computed(() => {
  const value = summary.value?.monitoringUrl?.trim()
  if (!value) return ''
  if (value.startsWith('/') && !value.startsWith('//')) return value
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) ? url.toString() : ''
  } catch {
    return ''
  }
})

const metrics = computed(() => {
  const value = summary.value
  return [
    { label: '总用户', value: formatNumber(value?.users.total), note: `${formatNumber(value?.users.admins)} 名管理员` },
    { label: '活跃用户', value: formatNumber(value?.users.active), note: `新增 ${formatNumber(value?.users.newUsers)}` },
    { label: '访问请求', value: formatNumber(value?.traffic.requests), note: `错误率 ${formatPercent(value?.traffic.errorRate)}` },
    { label: 'P95 延迟', value: formatLatency(value?.traffic.p95LatencyMs), note: 'HTTP 请求' },
    { label: '播放次数', value: formatNumber(value?.playback.plays), note: `跳过 ${formatNumber(value?.playback.skips)}` },
    { label: '收听时长', value: formatDuration(value?.playback.listenSeconds), note: `跳过率 ${formatSkipRate(value)}` },
  ]
})

watch(selectedRange, () => {
  void loadSummary()
})

onMounted(() => {
  void loadAll()
})

async function loadAll() {
  forbidden.value = false
  loadError.value = null
  await Promise.all([loadSummary(), loadUsers(usersPage.value.page)])
}

async function loadSummary() {
  isSummaryLoading.value = true
  try {
    summary.value = await fetchAdminStatsSummary(selectedRange.value)
  } catch (error) {
    handleError(error)
  } finally {
    isSummaryLoading.value = false
  }
}

async function loadUsers(page: number) {
  isUsersLoading.value = true
  try {
    usersPage.value = await fetchAdminUsers(page, PAGE_SIZE)
  } catch (error) {
    handleError(error)
  } finally {
    isUsersLoading.value = false
  }
}

function handleError(error: unknown) {
  if (error instanceof ApiError && error.status === 403) {
    forbidden.value = true
    return
  }
  loadError.value = error instanceof Error ? error.message : '管理数据加载失败'
}

function changePage(page: number) {
  if (page < 1 || page > totalPages.value) return
  void loadUsers(page)
}

function formatNumber(value: number | null | undefined): string {
  return value == null ? '--' : new Intl.NumberFormat('zh-CN').format(value)
}

function formatPercent(value: number | null | undefined): string {
  if (value == null) return '--'
  return `${(value * 100).toFixed(value >= 0.1 ? 1 : 2)}%`
}

function formatLatency(value: number | null | undefined): string {
  if (value == null) return '--'
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${Math.round(value)} ms`
}

function formatDuration(value: number | null | undefined): string {
  if (value == null) return '--'
  const hours = value / 3600
  if (hours >= 1) return `${hours.toFixed(hours >= 10 ? 0 : 1)} 小时`
  return `${Math.round(value / 60)} 分钟`
}

function formatSkipRate(value: AdminStatsSummary | null): string {
  if (!value || value.playback.plays <= 0) return '--'
  return formatPercent(value.playback.skips / value.playback.plays)
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '--' : date.toLocaleDateString('zh-CN')
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '--' : date.toLocaleString('zh-CN', { hour12: false })
}

function shortId(value: string): string {
  return value.length > 14 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value
}
</script>

<style scoped>
.admin-page {
  padding: 24px 32px 40px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.admin-header,
.section-heading,
.header-actions,
.title-line {
  display: flex;
  align-items: center;
}

.admin-header,
.section-heading {
  justify-content: space-between;
  gap: 20px;
}

.title-line {
  gap: 10px;
  color: var(--color-primary);
}

.title-line h1 {
  color: var(--color-text-primary);
  font-size: 26px;
  line-height: 1.2;
}

.admin-header p,
.section-heading p {
  margin-top: 5px;
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.header-actions {
  gap: 8px;
}

.grafana-link,
.refresh-btn,
.primary-link {
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-small);
}

.grafana-link {
  gap: 7px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 13px;
}

.grafana-link:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.refresh-btn {
  width: 36px;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

.refresh-btn:hover:not(:disabled) {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.refresh-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.range-tabs {
  width: fit-content;
  display: flex;
  padding: 3px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-small);
  background: var(--color-bg-content);
}

.range-tabs button {
  height: 30px;
  padding: 0 12px;
  border-radius: 5px;
  color: var(--color-text-secondary);
  font-size: 12px;
}

.range-tabs button.active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 600;
}

.metrics-section,
.users-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.metrics-section h2,
.section-heading h2 {
  font-size: 17px;
  color: var(--color-text-primary);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-small);
  overflow: hidden;
  background: var(--color-bg-content);
}

.metric-card {
  min-width: 0;
  min-height: 120px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-right: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.metric-card:nth-child(3n) {
  border-right: 0;
}

.metric-card:nth-last-child(-n + 3) {
  border-bottom: 0;
}

.metric-card span,
.metric-card small {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.metric-card strong {
  margin: 6px 0 4px;
  color: var(--color-text-primary);
  font-size: 25px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.user-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-small);
  background: var(--color-bg-content);
}

.user-table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  table-layout: fixed;
}

.user-table th,
.user-table td {
  height: 58px;
  padding: 0 16px;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  color: var(--color-text-secondary);
  font-size: 12px;
}

.user-table th {
  height: 42px;
  background: var(--color-bg-sidebar);
  color: var(--color-text-tertiary);
  font-weight: 600;
}

.user-table th:first-child {
  width: 32%;
}

.user-table tbody tr:last-child td {
  border-bottom: 0;
}

.user-cell {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-initial {
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 700;
}

.user-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.user-copy strong,
.user-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-copy strong {
  color: var(--color-text-primary);
  font-size: 13px;
}

.role-label,
.status-label {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 5px;
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
}

.role-label.admin {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.status-label.active {
  color: #18864b;
  background: rgba(24, 134, 75, 0.1);
}

.status-label.disabled {
  color: #b42318;
  background: rgba(180, 35, 24, 0.1);
}

.empty-row {
  text-align: center !important;
  color: var(--color-text-tertiary) !important;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  color: var(--color-text-secondary);
  font-size: 12px;
}

.pagination button {
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-small);
}

.pagination button:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.pagination button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.state-panel {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--color-text-secondary);
  text-align: center;
}

.state-panel h2 {
  margin-top: 4px;
  color: var(--color-text-primary);
  font-size: 18px;
}

.state-panel p {
  max-width: 420px;
  font-size: 13px;
}

.state-panel > .app-icon {
  color: var(--color-primary);
}

.primary-link {
  margin-top: 8px;
  padding: 0 16px;
  background: var(--color-primary);
  color: #fff;
  font-size: 13px;
}

.loading-label,
.inline-error {
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.inline-error {
  color: #b42318;
}

@media (max-width: 900px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-card:nth-child(3n) {
    border-right: 1px solid var(--color-border);
  }

  .metric-card:nth-child(2n) {
    border-right: 0;
  }

  .metric-card:nth-last-child(-n + 3) {
    border-bottom: 1px solid var(--color-border);
  }

  .metric-card:nth-last-child(-n + 2) {
    border-bottom: 0;
  }
}

@media (max-width: 640px) {
  .admin-page {
    padding: 20px;
  }

  .admin-header {
    align-items: flex-start;
  }

  .grafana-link span {
    display: none;
  }

  .grafana-link {
    width: 36px;
    padding: 0;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }

  .metric-card,
  .metric-card:nth-child(2n),
  .metric-card:nth-child(3n),
  .metric-card:nth-last-child(-n + 3) {
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
  }

  .metric-card:last-child {
    border-bottom: 0;
  }
}
</style>
