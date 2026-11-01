import { useState, useEffect } from 'react'
import { Plus, ChevronDown, Search, X } from 'lucide-react'
import { useLiveQuery } from 'dexie-react-hooks'
import { db, STATUS, STATUS_COLOR, PRIORITY_COLOR } from '../db'
import TaskDetail from './TaskDetail'
import TaskForm from './TaskForm'

export default function TasksPage() {
  const [projectId, setProjectId] = useState(null)
  const [filterStatus, setFilterStatus] = useState('すべて')
  const [search, setSearch] = useState('')
  const [selectedTask, setSelectedTask] = useState(null)
  const [showForm, setShowForm] = useState(false)

  const projects = useLiveQuery(() => db.projects.orderBy('createdAt').toArray(), [])
  const tasks = useLiveQuery(() => {
    let q = db.tasks.orderBy('createdAt')
    return q.toArray()
  }, [])

  useEffect(() => {
    if (projects?.length && !projectId) setProjectId(projects[0].id)
  }, [projects])

  const filtered = (tasks || []).filter(t => {
    if (projectId && t.projectId !== projectId) return false
    if (filterStatus !== 'すべて' && t.status !== filterStatus) return false
    if (search && !t.title.includes(search) && !(t.assignee || '').includes(search)) return false
    return true
  })

  const counts = (tasks || []).reduce((acc, t) => {
    if (!projectId || t.projectId === projectId) acc[t.status] = (acc[t.status] || 0) + 1
    return acc
  }, {})

  if (selectedTask) {
    return <TaskDetail task={selectedTask} onBack={() => setSelectedTask(null)} onUpdate={setSelectedTask} />
  }
  if (showForm) {
    return <TaskForm projectId={projectId} onClose={() => setShowForm(false)} />
  }

  return (
    <div className="flex flex-col h-full">
      {/* ヘッダー */}
      <div className="bg-blue-800 text-white px-4 pt-12 pb-4">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-lg font-bold">施工管理</h1>
          {projects?.length === 0 && (
            <button
              onClick={async () => {
                const id = await db.projects.add({ name: '新規工事', createdAt: Date.now() })
                setProjectId(id)
              }}
              className="text-xs bg-blue-600 px-3 py-1 rounded-full"
            >
              案件追加
            </button>
          )}
        </div>

        {/* 案件セレクト */}
        {projects && projects.length > 0 && (
          <div className="relative mb-3">
            <select
              value={projectId || ''}
              onChange={e => setProjectId(Number(e.target.value))}
              className="w-full bg-blue-700 text-white rounded-lg px-3 py-2 text-sm appearance-none pr-8 border border-blue-600"
            >
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <ChevronDown size={16} className="absolute right-2 top-2.5 text-blue-300 pointer-events-none" />
          </div>
        )}

        {/* 検索 */}
        <div className="relative">
          <Search size={15} className="absolute left-3 top-2.5 text-blue-300" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="タスクを検索..."
            className="w-full bg-blue-700 text-white placeholder-blue-300 rounded-lg pl-9 pr-9 py-2 text-sm border border-blue-600 outline-none"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2 top-2">
              <X size={16} className="text-blue-300" />
            </button>
          )}
        </div>
      </div>

      {/* ステータスフィルタ */}
      <div className="flex gap-2 px-4 py-3 overflow-x-auto bg-white border-b border-slate-200">
        {['すべて', ...STATUS].map(s => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            className={`flex-none text-xs px-3 py-1 rounded-full border transition-colors ${
              filterStatus === s
                ? 'bg-blue-700 text-white border-blue-700'
                : 'bg-slate-50 text-slate-600 border-slate-200'
            }`}
          >
            {s}
            {s !== 'すべて' && counts[s] ? ` (${counts[s]})` : ''}
          </button>
        ))}
      </div>

      {/* タスクリスト */}
      <div className="flex-1 overflow-y-auto">
        {!projects?.length ? (
          <EmptyProjects onAdd={async () => {
            const name = prompt('案件名を入力してください')
            if (!name) return
            const id = await db.projects.add({ name, createdAt: Date.now() })
            setProjectId(id)
          }} />
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400 text-sm">
            <p>タスクがありません</p>
          </div>
        ) : (
          <ul className="divide-y divide-slate-200 bg-white mx-0">
            {filtered.map(task => (
              <TaskCard key={task.id} task={task} onPress={() => setSelectedTask(task)} />
            ))}
          </ul>
        )}
      </div>

      {/* FAB */}
      {projects?.length > 0 && (
        <button
          onClick={() => setShowForm(true)}
          className="fixed bottom-20 right-4 w-14 h-14 bg-blue-700 text-white rounded-full shadow-lg flex items-center justify-center z-40"
        >
          <Plus size={28} />
        </button>
      )}
    </div>
  )
}

function TaskCard({ task, onPress }) {
  const sc = STATUS_COLOR[task.status] || STATUS_COLOR['未着手']
  const pc = task.priority ? PRIORITY_COLOR[task.priority] : null
  const today = new Date().toISOString().slice(0, 10)
  const overdue = task.endDate && task.endDate < today && task.status !== '完了'

  return (
    <li
      onClick={onPress}
      className="px-4 py-3 flex gap-3 items-start active:bg-slate-50 cursor-pointer"
    >
      <span
        className="mt-0.5 w-2.5 h-2.5 rounded-full flex-none"
        style={{ background: sc.dot }}
      />
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium text-slate-800 truncate ${task.status === '完了' ? 'line-through text-slate-400' : ''}`}>
          {task.title}
        </p>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: sc.bg, color: sc.text }}>
            {task.status}
          </span>
          {task.assignee && (
            <span className="text-xs text-slate-500">{task.assignee}</span>
          )}
          {pc && (
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: pc.bg, color: pc.text }}>
              {task.priority}
            </span>
          )}
          {task.endDate && (
            <span className={`text-xs ${overdue ? 'text-red-600 font-medium' : 'text-slate-400'}`}>
              {overdue ? '⚠ ' : ''}{task.endDate}
            </span>
          )}
          {task.photos?.length > 0 && (
            <span className="text-xs text-slate-400">📷 {task.photos.length}</span>
          )}
        </div>
      </div>
      <ChevronDown size={16} className="text-slate-300 -rotate-90 flex-none mt-1" />
    </li>
  )
}

function EmptyProjects({ onAdd }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
      <div className="text-5xl mb-4">🏗️</div>
      <p className="text-slate-600 font-medium mb-2">案件がありません</p>
      <p className="text-slate-400 text-sm mb-6">最初の施工案件を追加しましょう</p>
      <button
        onClick={onAdd}
        className="bg-blue-700 text-white px-6 py-2 rounded-full text-sm font-medium"
      >
        案件を追加
      </button>
    </div>
  )
}
