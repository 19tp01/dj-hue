import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import type { DJHueCommand, PatternListItem, PatternSaved, PatternDeleted, PatternSource, PatternValidated } from '../../hooks/useWebSocket'
import type { BankName, PaletteInfo } from '../../types'
import { PaletteChip } from '../Palettes/PaletteChip'

// Available tags for patterns (decorative, optional)
const AVAILABLE_TAGS = [
  'wave', 'flash', 'chase', 'pulse', 'fade',
  'rainbow', 'strobe', 'spatial', 'bounce', 'stereo',
  'autonomous', 'signature', 'classic',
]

// Categories in display order
const CATEGORIES: BankName[] = ['Ambient', 'Buildup', 'Chill', 'Upbeat']

interface PatternEditorProps {
  patternList: PatternListItem[] | null
  palettes: PaletteInfo[]
  patternSource: PatternSource | null
  patternSaved: PatternSaved | null
  patternDeleted: PatternDeleted | null
  patternValidated: PatternValidated | null
  onBack: () => void
  send: (command: DJHueCommand) => void
  clearPatternSource: () => void
  clearPatternSaved: () => void
  clearPatternDeleted: () => void
  clearPatternValidated: () => void
}

function BackIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-6 h-6"
    >
      <path d="M19 12H5M12 19l-7-7 7-7" />
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
      className="w-5 h-5"
    >
      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
    </svg>
  )
}

interface PatternRowProps {
  pattern: PatternListItem
  isSelected: boolean
  onSelect: () => void
  onDelete: () => void
}

function PatternRow({ pattern, isSelected, onSelect, onDelete }: PatternRowProps) {
  return (
    <div
      onClick={onSelect}
      className="flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors"
      style={{
        background: isSelected ? 'var(--accent-mid)' : 'transparent',
        borderLeft: isSelected ? '3px solid var(--accent-bright)' : '3px solid transparent',
      }}
    >
      <div className="flex-1 min-w-0">
        <div
          className="font-medium text-sm truncate"
          style={{ color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)' }}
        >
          {pattern.name}
        </div>
        {pattern.tags.length > 0 && (
          <div className="flex gap-1 mt-0.5">
            {pattern.tags.slice(0, 2).map(tag => (
              <span
                key={tag}
                className="text-xs px-1.5 py-0.5 rounded"
                style={{
                  background: 'var(--bg-interactive)',
                  color: 'var(--text-muted)',
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="p-1.5 rounded transition-colors opacity-50 hover:opacity-100"
        style={{ color: 'var(--text-muted)' }}
        aria-label="Delete"
      >
        <TrashIcon />
      </button>
    </div>
  )
}

interface EditPanelProps {
  pattern: PatternListItem
  body: string
  palettes: PaletteInfo[]
  onSave: (updated: PatternListItem, body: string) => void
  validationError: string | null
  isValidating: boolean
  message: { text: string; success: boolean } | null
}

function EditPanel({ pattern, body: initialBody, palettes, onSave, validationError, isValidating, message }: EditPanelProps) {
  const [name, setName] = useState(pattern.name)
  const [description, setDescription] = useState(pattern.description)
  const [category, setCategory] = useState<BankName>(pattern.category)
  const [tags, setTags] = useState<string[]>(pattern.tags)
  const [palette, setPalette] = useState<string | null>(pattern.palette)
  const [body, setBody] = useState(initialBody)
  const [isDirty, setIsDirty] = useState(false)

  // Reset form when pattern changes
  useEffect(() => {
    setName(pattern.name)
    setDescription(pattern.description)
    setCategory(pattern.category)
    setTags(pattern.tags)
    setPalette(pattern.palette)
    setBody(initialBody)
    setIsDirty(false)
  }, [pattern, initialBody])

  const handleChange = <T,>(setter: React.Dispatch<React.SetStateAction<T>>, value: T) => {
    setter(value)
    setIsDirty(true)
  }

  const handleTagToggle = (tag: string) => {
    setTags(prev => {
      const newTags = prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
      setIsDirty(true)
      return newTags
    })
  }

  const handleSave = () => {
    onSave({
      ...pattern,
      name,
      description,
      category,
      tags,
      palette,
    }, body)
  }

  // Clear dirty flag when save succeeds
  useEffect(() => {
    if (message?.success) {
      setIsDirty(false)
    }
  }, [message])

  const canSave = isDirty && !isValidating

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center justify-between shrink-0"
        style={{
          background: 'var(--bg-elevated)',
          borderBottom: '1px solid var(--bg-interactive)',
        }}
      >
        <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
          Edit Pattern
        </h2>
        <button
          onClick={handleSave}
          disabled={!canSave}
          className="px-4 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-40"
          style={{
            background: canSave ? 'var(--accent-mid)' : 'var(--bg-interactive)',
            color: 'var(--text-primary)',
          }}
        >
          {isValidating ? 'Validating...' : 'Save'}
        </button>
      </div>

      {/* Message */}
      {message && (
        <div
          className="mx-4 mt-3 py-2 px-3 rounded text-sm"
          style={{
            background: message.success ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
            color: message.success ? 'rgb(16, 185, 129)' : 'rgb(239, 68, 68)',
          }}
        >
          {message.text}
        </div>
      )}

      {/* Validation Error */}
      {validationError && (
        <div
          className="mx-4 mt-3 py-2 px-3 rounded text-sm"
          style={{
            background: 'rgba(239, 68, 68, 0.2)',
            color: 'rgb(239, 68, 68)',
          }}
        >
          {validationError}
        </div>
      )}

      {/* Form - scrollable */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Name */}
        <div>
          <label className="block text-sm mb-1.5" style={{ color: 'var(--text-muted)' }}>Name</label>
          <input
            type="text"
            value={name}
            onChange={e => handleChange(setName, e.target.value)}
            className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-1"
            style={{
              background: 'var(--bg-elevated)',
              borderColor: 'var(--bg-interactive)',
              color: 'var(--text-primary)',
            }}
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm mb-1.5" style={{ color: 'var(--text-muted)' }}>Description</label>
          <input
            type="text"
            value={description}
            onChange={e => handleChange(setDescription, e.target.value)}
            className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-1"
            style={{
              background: 'var(--bg-elevated)',
              borderColor: 'var(--bg-interactive)',
              color: 'var(--text-primary)',
            }}
          />
        </div>

        {/* Category (required) */}
        <div>
          <label className="block text-sm mb-2" style={{ color: 'var(--text-muted)' }}>Category</label>
          <div className="grid grid-cols-4 gap-2">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                onClick={() => handleChange(setCategory, cat)}
                className="py-2 px-2 text-sm rounded-lg transition-colors"
                style={{
                  background: category === cat ? 'var(--accent-mid)' : 'var(--bg-elevated)',
                  color: category === cat ? 'var(--text-primary)' : 'var(--text-muted)',
                  border: category === cat ? '1px solid var(--accent-bright)' : '1px solid var(--bg-interactive)',
                }}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Tags */}
        <div>
          <label className="block text-sm mb-2" style={{ color: 'var(--text-muted)' }}>Tags</label>
          <div className="flex flex-wrap gap-2">
            {AVAILABLE_TAGS.map(tag => (
              <button
                key={tag}
                onClick={() => handleTagToggle(tag)}
                className="px-3 py-1 text-sm rounded-full transition-colors"
                style={{
                  background: tags.includes(tag) ? 'var(--accent-mid)' : 'var(--bg-elevated)',
                  color: tags.includes(tag) ? 'var(--text-primary)' : 'var(--text-muted)',
                }}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Palette */}
        <div>
          <label className="block text-sm mb-2" style={{ color: 'var(--text-muted)' }}>Default Palette</label>
          <div className="flex flex-wrap gap-2">
            <PaletteChip
              name="None"
              isSelected={palette === null}
              isDefault
              onClick={() => { setPalette(null); setIsDirty(true) }}
            />
            {palettes.map(p => (
              <PaletteChip
                key={p.name}
                name={p.name}
                colors={p.colors}
                isSelected={palette === p.name}
                onClick={() => { setPalette(p.name); setIsDirty(true) }}
              />
            ))}
          </div>
        </div>

        {/* Pattern Code */}
        <div>
          <label className="block text-sm mb-2" style={{ color: 'var(--text-muted)' }}>
            Pattern Code
            <span className="ml-2 opacity-60">(Strudel DSL)</span>
          </label>
          <textarea
            value={body}
            onChange={e => handleChange(setBody, e.target.value)}
            spellCheck={false}
            className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-1 font-mono text-sm resize-none"
            style={{
              background: 'var(--bg-elevated)',
              borderColor: validationError ? 'rgb(239, 68, 68)' : 'var(--bg-interactive)',
              color: 'var(--text-primary)',
              minHeight: '200px',
            }}
            placeholder='light("all").color("cyan")'
          />
          <p className="mt-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
            Use light(), stack(), cat() with transforms like .color(), .fast(), .envelope()
          </p>
        </div>
      </div>
    </div>
  )
}

interface DeleteConfirmProps {
  patternName: string
  onConfirm: () => void
  onCancel: () => void
}

function DeleteConfirm({ patternName, onConfirm, onCancel }: DeleteConfirmProps) {
  return (
    <div
      className="fixed inset-0 flex items-center justify-center p-4 z-50"
      style={{ background: 'rgba(0,0,0,0.8)' }}
    >
      <div
        className="rounded-xl max-w-sm w-full p-6"
        style={{ background: 'var(--bg-surface)' }}
      >
        <h2 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
          Delete Pattern?
        </h2>
        <p className="mb-6" style={{ color: 'var(--text-muted)' }}>
          Are you sure you want to delete "{patternName}"? This cannot be undone.
        </p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-3 rounded-lg transition-colors"
            style={{
              background: 'var(--bg-elevated)',
              color: 'var(--text-secondary)',
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 py-3 rounded-lg transition-colors"
            style={{
              background: 'var(--status-error)',
              color: 'var(--text-primary)',
            }}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}

export function PatternEditor({
  patternList,
  palettes,
  patternSource,
  patternSaved,
  patternDeleted,
  patternValidated,
  onBack,
  send,
  clearPatternSource,
  clearPatternSaved,
  clearPatternDeleted,
  clearPatternValidated,
}: PatternEditorProps) {
  const [selectedPattern, setSelectedPattern] = useState<PatternListItem | null>(null)
  const [deletingPattern, setDeletingPattern] = useState<PatternListItem | null>(null)
  const [message, setMessage] = useState<{ text: string; success: boolean } | null>(null)
  const [currentBody, setCurrentBody] = useState<string>('')
  const [isLoadingBody, setIsLoadingBody] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [isValidating, setIsValidating] = useState(false)

  // Fetch pattern list on mount
  useEffect(() => {
    send({ type: 'get_pattern_list' })
  }, [send])

  // Auto-select first pattern when list loads
  useEffect(() => {
    if (patternList && patternList.length > 0 && !selectedPattern) {
      setSelectedPattern(patternList[0])
    }
  }, [patternList, selectedPattern])

  // Fetch pattern source when selected pattern changes
  useEffect(() => {
    if (selectedPattern) {
      setIsLoadingBody(true)
      setValidationError(null)
      send({ type: 'get_pattern_source', name: selectedPattern.name })
    }
  }, [selectedPattern?.filename, send])

  // Handle pattern source response
  useEffect(() => {
    if (patternSource) {
      setIsLoadingBody(false)
      if (patternSource.success && patternSource.body !== undefined) {
        setCurrentBody(patternSource.body)
      } else {
        setCurrentBody('')
      }
      clearPatternSource()
    }
  }, [patternSource, clearPatternSource])

  // Handle validation result
  useEffect(() => {
    if (patternValidated) {
      setIsValidating(false)
      if (patternValidated.valid) {
        setValidationError(null)
      } else {
        setValidationError(patternValidated.error || 'Invalid pattern')
      }
      clearPatternValidated()
    }
  }, [patternValidated, clearPatternValidated])

  // Ref to track the body that was just saved
  const savedBodyRef = useRef<string | null>(null)

  // Handle save result
  useEffect(() => {
    if (patternSaved) {
      if (patternSaved.success) {
        setMessage({ text: 'Saved', success: true })
        // Update currentBody to reflect the saved code
        if (savedBodyRef.current !== null) {
          setCurrentBody(savedBodyRef.current)
          savedBodyRef.current = null
        }
        send({ type: 'get_pattern_list' })
      } else {
        setMessage({ text: patternSaved.error || 'Save failed', success: false })
      }
      clearPatternSaved()
    }
  }, [patternSaved, clearPatternSaved, send])

  // Handle delete result
  useEffect(() => {
    if (patternDeleted) {
      if (patternDeleted.success) {
        setMessage({ text: 'Deleted', success: true })
        setDeletingPattern(null)
        setSelectedPattern(null)
        send({ type: 'get_pattern_list' })
      } else {
        setMessage({ text: patternDeleted.error || 'Delete failed', success: false })
      }
      clearPatternDeleted()
    }
  }, [patternDeleted, clearPatternDeleted, send])

  // Update selected pattern when list refreshes
  useEffect(() => {
    if (selectedPattern && patternList) {
      const updated = patternList.find(p => p.filename === selectedPattern.filename)
      if (updated) {
        setSelectedPattern(updated)
      }
    }
  }, [patternList, selectedPattern?.filename])

  // Clear message after delay
  useEffect(() => {
    if (message) {
      const timeout = setTimeout(() => setMessage(null), 2000)
      return () => clearTimeout(timeout)
    }
  }, [message])

  // Group patterns by category
  const patternsByCategory = useMemo(() => {
    const grouped: Record<BankName, PatternListItem[]> = {
      'Ambient': [],
      'Buildup': [],
      'Chill': [],
      'Upbeat': [],
    }
    patternList?.forEach(p => {
      const category = p.category && grouped[p.category] ? p.category : 'Chill'
      grouped[category].push(p)
    })
    return grouped
  }, [patternList])

  const handleSave = useCallback((updated: PatternListItem, body: string) => {
    // Validate before saving
    setIsValidating(true)
    send({ type: 'validate_pattern', body })

    // Store pending save data
    pendingSaveRef.current = { updated, body }
  }, [send])

  // Ref to store pending save data
  const pendingSaveRef = useRef<{ updated: PatternListItem; body: string } | null>(null)

  // Complete save after successful validation
  useEffect(() => {
    if (patternValidated?.valid && pendingSaveRef.current) {
      const { updated, body } = pendingSaveRef.current
      pendingSaveRef.current = null
      // Store the body so we can update state after save succeeds
      savedBodyRef.current = body
      send({
        type: 'save_pattern',
        filename: updated.filename,
        name: updated.name,
        description: updated.description,
        tags: updated.tags,
        palette: updated.palette,
        category: updated.category,
        body,
      })
    }
  }, [patternValidated, send])

  const handleDeleteConfirm = useCallback(() => {
    if (deletingPattern) {
      send({ type: 'delete_pattern', name: deletingPattern.name })
    }
  }, [deletingPattern, send])

  const loading = patternList === null

  return (
    <div
      className="h-screen flex flex-col"
      style={{ background: 'var(--bg-void)' }}
    >
      {/* Header */}
      <header
        className="flex items-center gap-3 px-4 py-3 shrink-0"
        style={{
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--bg-elevated)',
        }}
      >
        <button
          onClick={onBack}
          className="p-2 rounded-lg transition-colors active:scale-95"
          style={{ color: 'var(--text-muted)' }}
          aria-label="Back"
        >
          <BackIcon />
        </button>
        <h1 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>
          Pattern Editor
        </h1>
      </header>

      {/* Main content - two columns */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Pattern list */}
        <div
          className="w-[280px] shrink-0 flex flex-col overflow-hidden"
          style={{
            background: 'var(--bg-surface)',
            borderRight: '1px solid var(--bg-elevated)',
          }}
        >
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <span style={{ color: 'var(--text-muted)' }}>Loading...</span>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              {CATEGORIES.map(category => {
                const patterns = patternsByCategory[category]
                if (patterns.length === 0) return null
                return (
                  <div key={category}>
                    {/* Category header */}
                    <div
                      className="px-3 py-2 text-xs font-semibold uppercase tracking-wider sticky top-0"
                      style={{
                        background: 'var(--bg-elevated)',
                        color: 'var(--text-muted)',
                        borderBottom: '1px solid var(--bg-interactive)',
                      }}
                    >
                      {category}
                      <span className="ml-2 opacity-60">({patterns.length})</span>
                    </div>
                    {/* Patterns in category */}
                    {patterns.map(pattern => (
                      <PatternRow
                        key={pattern.filename}
                        pattern={pattern}
                        isSelected={selectedPattern?.filename === pattern.filename}
                        onSelect={() => {
                          setSelectedPattern(pattern)
                          // Set pattern for live preview
                          send({ type: 'set_pattern', name: pattern.name })
                        }}
                        onDelete={() => setDeletingPattern(pattern)}
                      />
                    ))}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right: Edit panel */}
        <div
          className="flex-1 overflow-hidden"
          style={{ background: 'var(--bg-surface)' }}
        >
          {selectedPattern ? (
            isLoadingBody ? (
              <div className="h-full flex items-center justify-center">
                <span style={{ color: 'var(--text-muted)' }}>Loading...</span>
              </div>
            ) : (
              <EditPanel
                key={selectedPattern.filename}
                pattern={selectedPattern}
                body={currentBody}
                palettes={palettes}
                onSave={handleSave}
                validationError={validationError}
                isValidating={isValidating}
                message={message}
              />
            )
          ) : (
            <div className="h-full flex items-center justify-center">
              <span style={{ color: 'var(--text-muted)' }}>Select a pattern to edit</span>
            </div>
          )}
        </div>
      </div>

      {/* Delete confirm modal */}
      {deletingPattern && (
        <DeleteConfirm
          patternName={deletingPattern.name}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeletingPattern(null)}
        />
      )}
    </div>
  )
}
