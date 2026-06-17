import Dexie from 'dexie'

export const db = new Dexie('KoujiKanri')

db.version(1).stores({
  projects: '++id, name, createdAt',
  tasks: '++id, projectId, status, assignee, startDate, endDate, createdAt',
  members: '++id, name',
})

// デフォルトメンバー初期化
db.on('populate', () => {
  db.members.bulkAdd([
    { name: '田中', role: '現場監督' },
    { name: '鈴木', role: '大工' },
    { name: '佐藤', role: '電気工事' },
  ])
})

export const STATUS = ['未着手', '進行中', '完了', '遅延']
export const PRIORITY = ['高', '中', '低']

export const STATUS_COLOR = {
  未着手: { bg: '#f3f4f6', text: '#4b5563', dot: '#9ca3af' },
  進行中: { bg: '#dbeafe', text: '#1d4ed8', dot: '#3b82f6' },
  完了:   { bg: '#dcfce7', text: '#15803d', dot: '#22c55e' },
  遅延:   { bg: '#fee2e2', text: '#b91c1c', dot: '#ef4444' },
}

export const PRIORITY_COLOR = {
  高: { bg: '#fee2e2', text: '#b91c1c' },
  中: { bg: '#fef9c3', text: '#854d0e' },
  低: { bg: '#f0fdf4', text: '#15803d' },
}
