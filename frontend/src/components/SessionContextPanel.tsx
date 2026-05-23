import { useChatStore } from '../stores/useChatStore'

export default function SessionContextPanel() {
  const sessionContext = useChatStore((s) => s.sessionContext)
  const sessionId = useChatStore((s) => s.sessionId)

  const items: { label: string; value: string }[] = [
    { label: 'Circuit', value: sessionContext.circuit ?? '—' },
    { label: 'Session', value: sessionContext.session_type ?? '—' },
    { label: 'Driver', value: sessionContext.driver ?? '—' },
    { label: 'Car #', value: sessionContext.car_number ?? '—' },
    { label: 'Session ID', value: sessionId },
  ]

  return (
    <div className="px-4 py-4 border-b border-zinc-800">
      <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
        Session Context
      </h2>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.label} className="flex justify-between items-center">
            <span className="text-xs text-zinc-400">{item.label}</span>
            <span className="text-xs text-zinc-200 font-mono truncate ml-2 max-w-[140px]">
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
