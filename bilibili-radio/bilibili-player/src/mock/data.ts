import type { Track } from '@/types'

/**
 * 占位数据。后端目前只支持「输入 BV号/链接播放单个视频」，
 * 没有搜索 / 推荐 / 收藏夹 API，这些页面先用假数据渲染 UI。
 * 每条曲目的 bvid 都是真实存在的示例，双击后可走真实播放链路。
 */

export const recommendTracks: Track[] = [
  {
    bvid: 'BV1GJ411x7h7',
    title: '【4K修复】经典动画片头合集 · 那些年一起追过的番',
    owner: '怀旧放映室',
    cover: 'https://picsum.photos/seed/bili1/320/200',
    duration: 243,
  },
  {
    bvid: 'BV1xx411c7mD',
    title: '深夜钢琴 · 适合一个人静静听的旋律',
    owner: '琴键上的猫',
    cover: 'https://picsum.photos/seed/bili2/320/200',
    duration: 318,
  },
  {
    bvid: 'BV1Bx411c7Ya',
    title: 'Lo-Fi 学习电台 · 专注两小时不断电',
    owner: 'ChillStudy',
    cover: 'https://picsum.photos/seed/bili3/320/200',
    duration: 421,
  },
  {
    bvid: 'BV1z4411c7Kr',
    title: '城市夜骑 Vlog · 一路向北的电子乐',
    owner: '夜行观察员',
    cover: 'https://picsum.photos/seed/bili4/320/200',
    duration: 276,
  },
  {
    bvid: 'BV1Ns41167zh',
    title: '古风翻唱 · 半盏流年',
    owner: '青栀阁',
    cover: 'https://picsum.photos/seed/bili5/320/200',
    duration: 254,
  },
]

export const hotTracks: Track[] = [
  {
    bvid: 'BV1hK4y1C7Uw',
    title: '今日热门 · 十分钟看懂宇宙的尺度',
    owner: '硬核科普君',
    cover: 'https://picsum.photos/seed/hot1/320/200',
    duration: 612,
  },
  {
    bvid: 'BV1kW411p7DG',
    title: '街头美食 · 凌晨四点的早市有多香',
    owner: '干饭不迟到',
    cover: 'https://picsum.photos/seed/hot2/320/200',
    duration: 489,
  },
  {
    bvid: 'BV1sV4y1e7fH',
    title: '手工耿新作 · 没有用但很热血',
    owner: '保定发明家',
    cover: 'https://picsum.photos/seed/hot3/320/200',
    duration: 355,
  },
  {
    bvid: 'BV1qM4y1P7wj',
    title: '猫咪的一天 · 治愈系纪录片',
    owner: '铲屎官日记',
    cover: 'https://picsum.photos/seed/hot4/320/200',
    duration: 198,
  },
  {
    bvid: 'BV1eN411Q7wG',
    title: '复古游戏音乐会 · 像素时代的回响',
    owner: '8bit乐团',
    cover: 'https://picsum.photos/seed/hot5/320/200',
    duration: 533,
  },
]

export interface MockFavFolder {
  id: string
  title: string
  cover: string
  count: number
  tracks: Track[]
}

export const favoriteFolders: MockFavFolder[] = [
  {
    id: 'fav_default',
    title: '默认收藏夹',
    cover: 'https://picsum.photos/seed/fav1/320/200',
    count: recommendTracks.length,
    tracks: recommendTracks,
  },
  {
    id: 'fav_study',
    title: '学习白噪音',
    cover: 'https://picsum.photos/seed/fav2/320/200',
    count: 3,
    tracks: hotTracks.slice(0, 3),
  },
  {
    id: 'fav_night',
    title: '深夜歌单',
    cover: 'https://picsum.photos/seed/fav3/320/200',
    count: hotTracks.length,
    tracks: hotTracks,
  },
]

export function getFavFolder(id: string): MockFavFolder | undefined {
  return favoriteFolders.find((f) => f.id === id)
}
