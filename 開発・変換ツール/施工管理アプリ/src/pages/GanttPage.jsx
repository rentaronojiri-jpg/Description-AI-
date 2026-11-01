import { useState, useRef, useEffect } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useLiveQuery } from 'dexie-react-hooks'
import { db, STATUS_COLOR } from '../db'

function getDaysInMonth(year, month) {
  return new Date(year, month + 1, 0).getDate()
}

function isoDate(y, m, d) {
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

const DAY_W = 32 // px per day

export default function GanttPage() {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const [projectId, setProjectId] = useState(null)
  const scrollRef = useRef(null)

  const projects = useLiveQuery(() => db.projects.toArray(), [])
  const tasks = useLiveQuery(() => db.tasks.toArray(), [])

  const currentProjectId = projectId || projects?.[0]?.id
  const filtered = (tasks || []).filter(t => t.projectId === currentProjectId && (t.startDate || t.endDate))

  const daysInMonth = getDaysInMonth(year, month)
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1)

  const monthStart = isoDate(year, month, 1)
  const monthEnd = isoDate(year, month, daysInMonth)

  const todayStr = today.toISOString().slice(0, 10)
  const todayDay = year === today.getFullYear() && month === today.getMonth() ? today.getDate() : null

  // 今月表示時は今日付近に自動スクロール
  useEffect(() => {
    if (todayDay && scrollRef.current) {
      const offset = Math.max(0, (todayDay - 4) * DAY_W)
      scrollRef.current.scrollLeft = offset
    }
  }, [todayDay, month])

  const prevMonth = () => {
    if (month === 0) { setYear(y => y - 1); setMonth(11) }
    else setMonth(m => m - 1)
  }
  const nextMonth = () => {
    if (month === 11) { setYear(y => y + 1); setMonth(0) }
    else setMonth(m => m + 1)
  }

  const getBar = (task) => {
    const start = task.startDate || task.endDate
    const end = task.endDate || task.startDate
    const clampedStart = start < monthStart ? monthStart : start
    const clampedEnd = end > monthEnd ? monthEnd : end

    if (clampedStart > monthEnd || clampedEnd < monthStart) return null

    const startDay = parseInt(clampedStart.slice(8), 10)
    const endDay = parseInt(clampedEnd.slice(8), 10)
    const left = (startDay - 1) * DAY_W
    const width = (endDay - startDay + 1) * DAY_W - 2

    return { left, width }
  }

  const MONTH_NAMES = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
  const DOW = ['日', '月', '火', '水', '木', '金', '土']

  return (
    <div className="flex flex-col min-h-dvh">
      {/* ヘッダー */}
      <div className="bg-blue-800 text-white px-4 pt-12 pb-4">
        <h1 className="text-lg font-bold mb-3">工程表</h1>

        {projects && projects.length > 0 && (
          <select
            value={currentProjectId || ''}
            onChange={e => setProjectId(Number(e.target.value))}
            className="w-full bg-blue-700 text-white rounded-lg px-3 py-2 text-sm border border-blue-600"
          >
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        )}

        <div className="flex items-center justify-between mt-3">
          <button onClick={prevMonth} className="p-1 text-blue-300">
            <ChevronLeft size={20} />
          </button>
          <span className="font-bold">{year}年 {MONTH_NAMES[month]}</span>
          <button onClick={nextMonth} className="p-1 text-blue-300">
            <ChevronRight size={20} />
          </button>
        </div>
      </div>

      {/* ガントチャート本体 */}
      <div className="flex-1 overflow-hidden bg-white">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400 text-sm">
            <p>この月に表示できるタスクがありません</p>
            <p className="text-xs mt-1">タスクに開始日・終了日を設定してください</p>
          </div>
        ) : (
          <div className="overflow-x-auto overflow-y-auto gantt-scroll" ref={scrollRef}>
            {/* タスク名カラム幅 */}
            <div style={{ minWidth: 120 + daysInMonth * DAY_W }}>
              {/* 日付ヘッダー */}
              <div className="flex sticky top-0 bg-white z-10 border-b border-slate-200">
                <div className="w-28 flex-none text-xs text-slate-400 px-2 py-2 border-r border-slate-200 font-medium">
                  タスク
                </div>
                <div className="flex">
                  {days.map(d => {
                    const dow = new Date(year, month, d).getDay()
                    const isToday = todayDay === d
                    return (
                      <div
                        key={d}
                        style={{ width: DAY_W }}
                        className={`flex-none text-center text-xs py-1 border-r border-slate-100 ${
                          isToday ? 'bg-blue-50 font-bold text-blue-700' :
                          dow === 0 ? 'text-red-400' :
                          dow === 6 ? 'text-blue-400' : 'text-slate-500'
                        }`}
                      >
                        <div>{d}</div>
                        <div className="text-[10px]">{DOW[dow]}</div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* タスク行 */}
              {filtered.map(task => {
                const bar = getBar(task)
                const sc = STATUS_COLOR[task.status] || STATUS_COLOR['未着手']
                return (
                  <div key={task.id} className="flex border-b border-slate-100 h-10 items-center">
                    {/* タスク名 */}
                    <div className="w-28 flex-none px-2 border-r border-slate-200 h-full flex items-center">
                      <span className="text-xs text-slate-700 truncate">{task.title}</span>
                    </div>

                    {/* ガントバー領域 */}
                    <div className="relative flex h-full" style={{ width: daysInMonth * DAY_W }}>
                      {/* 今日ライン */}
                      {todayDay && (
                        <div
                          className="absolute top-0 bottom-0 w-px bg-blue-400 z-10 pointer-events-none"
                          style={{ left: (todayDay - 0.5) * DAY_W }}
                        />
                      )}

                      {/* グリッド */}
                      {days.map(d => {
                        const dow = new Date(year, month, d).getDay()
                        return (
                          <div
                            key={d}
                            style={{ width: DAY_W }}
                            className={`flex-none h-full border-r border-slate-100 ${
                              dow === 0 || dow === 6 ? 'bg-slate-50' : ''
                            }`}
                          />
                        )
                      })}

                      {/* バー */}
                      {bar && (
                        <div
                          className="absolute top-1/2 -translate-y-1/2 h-5 rounded flex items-center px-1.5"
                          style={{
                            left: bar.left + 1,
                            width: bar.width,
                            background: sc.dot,
                            opacity: task.status === '完了' ? 0.5 : 1,
                          }}
                        >
                          <span className="text-white text-[10px] truncate font-medium">
                            {task.status === '完了' ? '✓ ' : ''}{task.assignee || ''}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* 凡例 */}
      <div className="bg-white border-t border-slate-200 px-4 py-2 flex gap-4 flex-wrap">
        {Object.entries(STATUS_COLOR).map(([s, c]) => (
          <div key={s} className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className="w-3 h-3 rounded-sm" style={{ background: c.dot }} />
            {s}
          </div>
        ))}
      </div>
    </div>
  )
}
