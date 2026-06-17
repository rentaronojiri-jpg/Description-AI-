import { useState } from 'react'
import { Plus, Trash2, Building2, Users } from 'lucide-react'
import { useLiveQuery } from 'dexie-react-hooks'
import { db } from '../db'

export default function SettingsPage() {
  const [tab, setTab] = useState('projects')

  return (
    <div className="flex flex-col min-h-dvh">
      <div className="bg-blue-800 text-white px-4 pt-12 pb-4">
        <h1 className="text-lg font-bold">設定</h1>
      </div>

      <div className="flex bg-white border-b border-slate-200">
        <TabBtn active={tab === 'projects'} onClick={() => setTab('projects')} icon={<Building2 size={16} />}>
          案件管理
        </TabBtn>
        <TabBtn active={tab === 'members'} onClick={() => setTab('members')} icon={<Users size={16} />}>
          メンバー
        </TabBtn>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'projects' && <ProjectsPanel />}
        {tab === 'members' && <MembersPanel />}
      </div>
    </div>
  )
}

function TabBtn({ active, onClick, icon, children }) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 flex items-center justify-center gap-1.5 py-3 text-sm border-b-2 transition-colors ${
        active ? 'border-blue-700 text-blue-700 font-medium' : 'border-transparent text-slate-500'
      }`}
    >
      {icon}{children}
    </button>
  )
}

function ProjectsPanel() {
  const [name, setName] = useState('')
  const projects = useLiveQuery(() => db.projects.orderBy('createdAt').toArray(), [])

  const add = async () => {
    if (!name.trim()) return
    await db.projects.add({ name: name.trim(), createdAt: Date.now() })
    setName('')
  }

  const remove = async (id) => {
    if (!confirm('案件とそのタスクをすべて削除しますか？')) return
    await db.tasks.where('projectId').equals(id).delete()
    await db.projects.delete(id)
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="案件名を入力"
          className="flex-1 border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-blue-500"
        />
        <button
          onClick={add}
          className="bg-blue-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium flex items-center gap-1"
        >
          <Plus size={16} /> 追加
        </button>
      </div>

      {projects?.length === 0 ? (
        <p className="text-center text-slate-400 text-sm py-8">案件がありません</p>
      ) : (
        <ul className="bg-white rounded-xl divide-y divide-slate-100 border border-slate-200">
          {projects?.map(p => (
            <li key={p.id} className="flex items-center px-4 py-3 gap-3">
              <Building2 size={16} className="text-slate-400 flex-none" />
              <span className="flex-1 text-sm text-slate-700">{p.name}</span>
              <button onClick={() => remove(p.id)} className="text-red-400 p-1">
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function MembersPanel() {
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const members = useLiveQuery(() => db.members.toArray(), [])

  const add = async () => {
    if (!name.trim()) return
    await db.members.add({ name: name.trim(), role: role.trim() })
    setName('')
    setRole('')
  }

  const remove = async (id) => {
    await db.members.delete(id)
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="flex gap-2">
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="氏名"
            className="flex-1 border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-blue-500"
          />
          <input
            value={role}
            onChange={e => setRole(e.target.value)}
            placeholder="役職"
            className="w-28 border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-blue-500"
          />
        </div>
        <button
          onClick={add}
          className="w-full bg-blue-700 text-white py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-1"
        >
          <Plus size={16} /> メンバー追加
        </button>
      </div>

      {members?.length === 0 ? (
        <p className="text-center text-slate-400 text-sm py-8">メンバーがいません</p>
      ) : (
        <ul className="bg-white rounded-xl divide-y divide-slate-100 border border-slate-200">
          {members?.map(m => (
            <li key={m.id} className="flex items-center px-4 py-3 gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 text-xs font-bold flex-none">
                {m.name[0]}
              </div>
              <div className="flex-1">
                <p className="text-sm text-slate-700">{m.name}</p>
                {m.role && <p className="text-xs text-slate-400">{m.role}</p>}
              </div>
              <button onClick={() => remove(m.id)} className="text-red-400 p-1">
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
