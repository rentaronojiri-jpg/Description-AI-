import { useState } from 'react'
import { ArrowLeft, Edit2, Calendar, User, AlertCircle } from 'lucide-react'
import { db, STATUS, STATUS_COLOR, PRIORITY_COLOR } from '../db'
import TaskForm from './TaskForm'

export default function TaskDetail({ task, onBack, onUpdate }) {
  const [editing, setEditing] = useState(false)

  if (editing) {
    return <TaskForm task={task} projectId={task.projectId} onClose={() => {
      db.tasks.get(task.id).then(t => { onUpdate(t); setEditing(false) })
    }} />
  }

  const sc = STATUS_COLOR[task.status] || STATUS_COLOR['未着手']
  const pc = task.priority ? PRIORITY_COLOR[task.priority] : null

  const today = new Date().toISOString().slice(0, 10)
  const overdue = task.endDate && task.endDate < today && task.status !== '完了'

  const cycleStatus = async () => {
    const idx = STATUS.indexOf(task.status)
    const next = STATUS[(idx + 1) % STATUS.length]
    await db.tasks.update(task.id, { status: next, updatedAt: Date.now() })
    onUpdate({ ...task, status: next })
  }

  return (
    <div className="flex flex-col min-h-dvh bg-slate-50">
      {/* ヘッダー */}
      <div className="bg-white border-b border-slate-200 px-4 pt-12 pb-3 flex items-center gap-3">
        <button onClick={onBack} className="text-slate-500 -ml-1">
          <ArrowLeft size={22} />
        </button>
        <h1 className="flex-1 text-base font-bold text-slate-800 truncate">{task.title}</h1>
        <button onClick={() => setEditing(true)} className="text-slate-500">
          <Edit2 size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* ステータス・優先度 */}
        <div className="bg-white rounded-xl p-4 flex flex-wrap gap-2 items-center">
          <button
            onClick={cycleStatus}
            className="px-3 py-1.5 rounded-full text-sm font-medium transition-colors"
            style={{ background: sc.bg, color: sc.text }}
          >
            {task.status} →
          </button>
          {pc && (
            <span className="px-3 py-1.5 rounded-full text-sm" style={{ background: pc.bg, color: pc.text }}>
              優先度: {task.priority}
            </span>
          )}
          {overdue && (
            <span className="flex items-center gap-1 text-red-600 text-xs">
              <AlertCircle size={14} /> 期限超過
            </span>
          )}
        </div>

        {/* 情報カード */}
        <div className="bg-white rounded-xl divide-y divide-slate-100">
          <InfoRow icon={<User size={15} />} label="担当者" value={task.assignee || '未設定'} />
          <InfoRow icon={<Calendar size={15} />} label="開始日" value={task.startDate || '未設定'} />
          <InfoRow
            icon={<Calendar size={15} />}
            label="終了日"
            value={task.endDate || '未設定'}
            valueClass={overdue ? 'text-red-600 font-medium' : ''}
          />
        </div>

        {/* 詳細 */}
        {task.description && (
          <div className="bg-white rounded-xl p-4">
            <p className="text-xs font-medium text-slate-400 mb-2">詳細・メモ</p>
            <p className="text-sm text-slate-700 whitespace-pre-wrap">{task.description}</p>
          </div>
        )}

        {/* 写真 */}
        {task.photos?.length > 0 && (
          <div className="bg-white rounded-xl p-4">
            <p className="text-xs font-medium text-slate-400 mb-3">現場写真 ({task.photos.length})</p>
            <div className="grid grid-cols-2 gap-2">
              {task.photos.map(p => (
                <img
                  key={p.id}
                  src={p.data}
                  alt={p.name}
                  className="w-full aspect-square object-cover rounded-lg"
                  onClick={() => window.open(p.data)}
                />
              ))}
            </div>
          </div>
        )}

        <p className="text-center text-xs text-slate-300 pb-2">
          更新: {task.updatedAt ? new Date(task.updatedAt).toLocaleString('ja-JP') : '-'}
        </p>
      </div>
    </div>
  )
}

function InfoRow({ icon, label, value, valueClass = '' }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <span className="text-slate-400">{icon}</span>
      <span className="text-xs text-slate-400 w-16 flex-none">{label}</span>
      <span className={`text-sm text-slate-700 ${valueClass}`}>{value}</span>
    </div>
  )
}
