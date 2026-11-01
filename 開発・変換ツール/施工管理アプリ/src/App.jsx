import { useState } from 'react'
import { LayoutList, BarChart2, Settings } from 'lucide-react'
import TasksPage from './pages/TasksPage'
import GanttPage from './pages/GanttPage'
import SettingsPage from './pages/SettingsPage'

const TABS = [
  { id: 'tasks', label: 'タスク', icon: LayoutList },
  { id: 'gantt', label: '工程表', icon: BarChart2 },
  { id: 'settings', label: '設定', icon: Settings },
]

export default function App() {
  const [tab, setTab] = useState('tasks')

  return (
    <div className="flex flex-col min-h-dvh bg-slate-100">
      <div className="flex-1 overflow-y-auto pb-16">
        {tab === 'tasks' && <TasksPage />}
        {tab === 'gantt' && <GanttPage />}
        {tab === 'settings' && <SettingsPage />}
      </div>

      <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[430px] bg-white border-t border-slate-200 flex z-50">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex-1 flex flex-col items-center justify-center py-2 gap-0.5 text-xs transition-colors ${
              tab === id ? 'text-blue-700' : 'text-slate-400'
            }`}
          >
            <Icon size={22} strokeWidth={tab === id ? 2.5 : 1.8} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}
