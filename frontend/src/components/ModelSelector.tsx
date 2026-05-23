import { useChatStore } from '../stores/useChatStore'

const AVAILABLE_MODELS = [
  'qwen2.5:7b',
  'qwen2.5:14b',
  'llama3.2:8b',
  'mistral:7b',
  'deepseek-r1:7b',
]

export default function ModelSelector() {
  const model = useChatStore((s) => s.model)
  const setModel = useChatStore((s) => s.setModel)

  return (
    <div className="px-4 py-3 border-t border-zinc-800">
      <label
        htmlFor="model-select"
        className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-1.5"
      >
        LLM Model
      </label>
      <select
        id="model-select"
        value={model}
        onChange={(e) => setModel(e.target.value)}
        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm
                   text-zinc-200 focus:outline-none focus:ring-2 focus:ring-red-600
                   focus:border-transparent transition-colors cursor-pointer"
      >
        {AVAILABLE_MODELS.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    </div>
  )
}
