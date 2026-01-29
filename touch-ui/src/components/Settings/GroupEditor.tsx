import { useState, useCallback } from 'react'
import type { LightInfo } from '../../hooks/useWebSocket'

interface GroupEditorProps {
  customGroups: Record<string, string[]>
  lights: LightInfo[]
  onChange: (groups: Record<string, string[]>) => void
}

function PlusIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-5 h-5"
    >
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
    >
      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2" />
    </svg>
  )
}

function EditIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
    >
      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  )
}

interface GroupEditModalProps {
  groupName: string
  lightNames: string[]
  allLights: LightInfo[]
  isNew: boolean
  onSave: (name: string, lights: string[]) => void
  onCancel: () => void
}

function GroupEditModal({
  groupName,
  lightNames,
  allLights,
  isNew,
  onSave,
  onCancel,
}: GroupEditModalProps) {
  const [name, setName] = useState(groupName)
  const [selectedLights, setSelectedLights] = useState<Set<string>>(new Set(lightNames))
  const [error, setError] = useState<string | null>(null)

  const handleToggleLight = (lightName: string) => {
    setSelectedLights(prev => {
      const next = new Set(prev)
      if (next.has(lightName)) {
        next.delete(lightName)
      } else {
        next.add(lightName)
      }
      return next
    })
  }

  const handleSave = () => {
    const trimmedName = name.trim().toLowerCase().replace(/\s+/g, '_')
    if (!trimmedName) {
      setError('Group name is required')
      return
    }
    if (!/^[a-z][a-z0-9_]*$/.test(trimmedName)) {
      setError('Name must start with a letter and contain only letters, numbers, underscores')
      return
    }
    if (selectedLights.size === 0) {
      setError('Select at least one light')
      return
    }
    onSave(trimmedName, Array.from(selectedLights))
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
      <div className="bg-zinc-900 rounded-xl w-full max-w-md max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-zinc-800">
          <h3 className="text-lg font-semibold">
            {isNew ? 'Create Group' : 'Edit Group'}
          </h3>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Group name input */}
          <div>
            <label className="block text-sm text-zinc-400 mb-2">Group Name</label>
            <input
              type="text"
              value={name}
              onChange={e => {
                setName(e.target.value)
                setError(null)
              }}
              placeholder="e.g., ceiling, dancefloor"
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Light selection */}
          <div>
            <label className="block text-sm text-zinc-400 mb-2">
              Lights ({selectedLights.size} selected)
            </label>
            <div className="space-y-2">
              {allLights.map(light => (
                <label
                  key={light.rid}
                  className="flex items-center gap-3 p-3 bg-zinc-800 rounded-lg cursor-pointer hover:bg-zinc-750"
                >
                  <input
                    type="checkbox"
                    checked={selectedLights.has(light.name)}
                    onChange={() => handleToggleLight(light.name)}
                    className="w-5 h-5 rounded border-zinc-600 text-cyan-500 focus:ring-cyan-500 focus:ring-offset-zinc-900"
                  />
                  <span className="text-white">{light.name}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="text-red-400 text-sm">{error}</div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-zinc-800 flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-3 bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex-1 py-3 bg-cyan-600 text-white rounded-lg hover:bg-cyan-500 transition-colors"
          >
            {isNew ? 'Create' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}

export function GroupEditor({ customGroups, lights, onChange }: GroupEditorProps) {
  const [editingGroup, setEditingGroup] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  const handleCreate = useCallback(() => {
    setIsCreating(true)
    setEditingGroup(null)
  }, [])

  const handleEdit = useCallback((groupName: string) => {
    setEditingGroup(groupName)
    setIsCreating(false)
  }, [])

  const handleDelete = useCallback((groupName: string) => {
    const newGroups = { ...customGroups }
    delete newGroups[groupName]
    onChange(newGroups)
  }, [customGroups, onChange])

  const handleSave = useCallback((name: string, lightNames: string[]) => {
    const newGroups = { ...customGroups }
    // If editing and name changed, delete old entry
    if (editingGroup && editingGroup !== name) {
      delete newGroups[editingGroup]
    }
    newGroups[name] = lightNames
    onChange(newGroups)
    setEditingGroup(null)
    setIsCreating(false)
  }, [customGroups, editingGroup, onChange])

  const handleCancel = useCallback(() => {
    setEditingGroup(null)
    setIsCreating(false)
  }, [])

  const groupNames = Object.keys(customGroups)

  return (
    <div className="space-y-3">
      {/* Existing groups */}
      {groupNames.length === 0 ? (
        <div className="bg-zinc-900 rounded-lg p-6 text-center text-zinc-500">
          No custom groups defined
        </div>
      ) : (
        groupNames.map(name => (
          <div key={name} className="bg-zinc-900 rounded-lg p-3 flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <div className="text-cyan-400 font-mono">{name}</div>
              <div className="text-zinc-500 text-sm truncate">
                {customGroups[name].join(', ')}
              </div>
            </div>
            <button
              onClick={() => handleEdit(name)}
              className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded transition-colors"
              aria-label="Edit group"
            >
              <EditIcon />
            </button>
            <button
              onClick={() => handleDelete(name)}
              className="p-2 text-zinc-400 hover:text-red-400 hover:bg-zinc-800 rounded transition-colors"
              aria-label="Delete group"
            >
              <TrashIcon />
            </button>
          </div>
        ))
      )}

      {/* Add group button */}
      <button
        onClick={handleCreate}
        className="w-full py-3 bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white rounded-lg flex items-center justify-center gap-2 transition-colors"
      >
        <PlusIcon />
        Add Custom Group
      </button>

      {/* Edit/Create modal */}
      {(isCreating || editingGroup) && (
        <GroupEditModal
          groupName={editingGroup ?? ''}
          lightNames={editingGroup ? customGroups[editingGroup] : []}
          allLights={lights}
          isNew={isCreating}
          onSave={handleSave}
          onCancel={handleCancel}
        />
      )}
    </div>
  )
}
