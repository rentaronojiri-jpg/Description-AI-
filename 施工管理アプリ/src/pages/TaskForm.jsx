import { useState } from 'react'
import { X, Camera } from 'lucide-react'
import { useLiveQuery } from 'dexie-react-hooks'
import { db, STATUS, PRIORITY } from '../db'

export default function TaskForm({ projectId, task, onClose }) {
  const members = useLiveQuery(() => db.members.toArray(), [])
  const isEdit = !!task

  const [form, setForm] = useState({
    title: task?.title || '',
    description: task?.description || '',
    assignee: task?.assignee || '',
    status: task?.status || '未着手',
    priority: task?.priority || '中',
    startDate: task?.startDate || '',
    endDate: task?.endDate || '',
    photos: task?.photos || [],
  })

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const handlePhoto = async (e) => {
    const files = Array.from(e.target.files)
    const results = await Promise.all(files.map(file => new Promise(resolve => {
      const reader = new FileReader()
      reader.onload = () => resolve({ name: file.name, data: reader.result, id: Date.now() + Math.random() })
      reader.readAsDataURL(file)
    })))
    set('photos', [...form.photos, ...results])
  }

  const removePhoto = (id) => set('photos', form.photos.filter(p => p.id !== id))

  const handleSubmit = async () => {
    if (!form.title.trim()) return alert('タイトルを入力してください')
    const data = { ...form, projectId, updatedAt: Date.now() }
    if (isEdit) {
      await db.tasks.update(task.id, data)
    } else {
      await db.tasks.add({ ...data, createdAt: Date.now() })
    }
    onClose()
  }

  return (
    <div className="flex flex-col min-h-dvh bg-white">
      {/* ヘッダー */}
      <div className="flex items-center justify-between px-4 pt-12 pb-3 border-b border-slate-200 bg-white">
        <button onClick={onClose} className="text-slate-500">
          <X size={22} />
        </button>
        <h2 className="text-base font-bold text-slate-800">
          {isEdit ? 'タスクを編集' : 'タスクを追加'}
        </h2>
        <button onClick={handleSubmit} className="text-blue-700 font-bold text-sm">
          保存
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* タイトル */}
        <Field label="タスク名 *">
          <input
            value={form.title}
            onChange={e => set('title', e.target.value)}
            placeholder="例: 基礎コンクリート打設"
            className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-blue-500"
          />
        </Field>

        {/* 説明 */}
        <Field label="詳細・メモ">
          <textarea
            value={form.description}
            onChange={e => set('description', e.target.value)}
            rows={3}
            placeholder="作業内容の詳細..."
            className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-blue-500 resize-none"
          />
        </Field>

        {/* 担当者 */}
        <Field label="担当者">
          <div className="flex gap-2 flex-wrap mb-2">
            {members?.map(m => (
              <button
                key={m.id}
                onClick={() => set('assignee', form.assignee === m.name ? '' : m.name)}
                className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                  form.assignee === m.name
                    ? 'bg-blue-700 text-white border-blue-700'
                    : 'bg-slate-50 text-slate-600 border-slate-200'
                }`}
              >
                {m.name}
              </button>
            ))}
          </div>
          <input
            value={form.assignee}
            onChange={e => set('assignee', e.target.value)}
            placeholder="または直接入力"
            className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-blue-500"
          />
        </Field>

        {/* ステータス・優先度 */}
        <div className="grid grid-cols-2 gap-3">
          <Field label="ステータス">
            <select
              value={form.status}
              onChange={e => set('status', e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-blue-500 bg-white"
            >
              {STATUS.map(s => <option key={s}>{s}</option>)}
            </select>
          </Field>
          <Field label="優先度">
            <select
              value={form.priority}
              onChange={e => set('priority', e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-blue-500 bg-white"
            >
              {PRIORITY.map(p => <option key={p}>{p}</option>)}
            </select>
          </Field>
        </div>

        {/* 日程 */}
        <div className="grid grid-cols-2 gap-3">
          <Field label="開始日">
            <input
              type="date"
              value={form.startDate}
              onChange={e => set('startDate', e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-blue-500"
            />
          </Field>
          <Field label="終了日">
            <input
              type="date"
              value={form.endDate}
              onChange={e => set('endDate', e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-blue-500"
            />
          </Field>
        </div>

        {/* 写真 */}
        <Field label="現場写真">
          <label className="flex items-center gap-2 w-full border-2 border-dashed border-slate-200 rounded-lg p-3 text-sm text-slate-500 cursor-pointer hover:border-blue-400 transition-colors">
            <Camera size={18} className="text-slate-400" />
            写真を追加
            <input type="file" accept="image/*" multiple className="hidden" onChange={handlePhoto} />
          </label>
          {form.photos.length > 0 && (
            <div className="grid grid-cols-3 gap-2 mt-2">
              {form.photos.map(p => (
                <div key={p.id} className="relative aspect-square">
                  <img src={p.data} alt={p.name} className="w-full h-full object-cover rounded-lg" />
                  <button
                    onClick={() => removePhoto(p.id)}
                    className="absolute top-1 right-1 bg-black/60 rounded-full p-0.5"
                  >
                    <X size={12} className="text-white" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </Field>
      </div>

      {/* 削除ボタン（編集時のみ） */}
      {isEdit && (
        <div className="p-4 border-t border-slate-100">
          <button
            onClick={async () => {
              if (!confirm('このタスクを削除しますか？')) return
              await db.tasks.delete(task.id)
              onClose()
            }}
            className="w-full py-3 text-red-600 text-sm font-medium"
          >
            タスクを削除
          </button>
        </div>
      )}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-500 mb-1.5">{label}</label>
      {children}
    </div>
  )
}
