import { useEffect, useLayoutEffect, useRef, useState, type ComponentType, type MouseEvent as ReactMouseEvent } from 'react'

export type TimelineContextMenuAction = Readonly<{
  id: string
  label: string
  shortcut?: string
  icon?: ComponentType<{ 'aria-hidden'?: boolean; size?: number; strokeWidth?: number }>
  disabled?: boolean
  danger?: boolean
  separatorBefore?: boolean
  onSelect: () => void
}>

export type TimelineContextMenuModel = Readonly<{
  x: number
  y: number
  title: string
  subtitle?: string
  actions: readonly TimelineContextMenuAction[]
  onClose: () => void
}>

function enabledIndexes(actions: readonly TimelineContextMenuAction[]) {
  return actions.reduce<number[]>((indexes, action, index) => {
    if (!action.disabled) indexes.push(index)
    return indexes
  }, [])
}

function nextEnabled(actions: readonly TimelineContextMenuAction[], current: number, direction: 1 | -1) {
  const indexes = enabledIndexes(actions)
  if (!indexes.length) return -1
  const currentIndex = indexes.indexOf(current)
  const nextIndex = currentIndex < 0
    ? (direction > 0 ? 0 : indexes.length - 1)
    : (currentIndex + direction + indexes.length) % indexes.length
  return indexes[nextIndex]
}

export function TimelineContextMenu({ x, y, title, subtitle, actions, onClose }: TimelineContextMenuModel) {
  const menuRef = useRef<HTMLDivElement>(null)
  const [activeIndex, setActiveIndex] = useState(() => nextEnabled(actions, -1, 1))
  const [position, setPosition] = useState({ left: x, top: y })

  useLayoutEffect(() => {
    const menu = menuRef.current
    if (!menu) return
    const bounds = menu.getBoundingClientRect()
    const gutter = 8
    setPosition({
      left: Math.max(gutter, Math.min(x, window.innerWidth - bounds.width - gutter)),
      top: Math.max(gutter, Math.min(y, window.innerHeight - bounds.height - gutter)),
    })
  }, [x, y, actions.length])

  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null
    return () => previousFocus?.focus()
  }, [])

  useEffect(() => {
    const menu = menuRef.current
    if (!menu) return
    const active = activeIndex >= 0 ? menu.querySelector<HTMLElement>(`[data-menu-index="${activeIndex}"]`) : null
    active?.focus()
  }, [activeIndex])

  useEffect(() => {
    const handlePointerDown = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) onClose()
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault()
        setActiveIndex((current) => nextEnabled(actions, current, event.key === 'ArrowDown' ? 1 : -1))
        return
      }
      if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault()
        const indexes = enabledIndexes(actions)
        setActiveIndex(indexes.length ? (event.key === 'Home' ? indexes[0] : indexes.at(-1)!) : -1)
        return
      }
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        if (activeIndex >= 0 && !actions[activeIndex]?.disabled) {
          actions[activeIndex].onSelect()
          onClose()
        }
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [actions, activeIndex, onClose])

  function handleContextMenu(event: ReactMouseEvent) {
    event.preventDefault()
  }

  return (
    <div
      ref={menuRef}
      className="timeline-context-menu"
      role="menu"
      aria-label={title}
      style={{ left: position.left, top: position.top }}
      onContextMenu={handleContextMenu}
    >
      <div className="timeline-context-menu-header">
        <strong>{title}</strong>
        {subtitle ? <span>{subtitle}</span> : null}
      </div>
      <div className="timeline-context-menu-items">
        {actions.map((action, index) => {
          const Icon = action.icon
          return (
            <div key={action.id} className={action.separatorBefore ? 'timeline-context-menu-separator' : undefined}>
              {action.separatorBefore ? <span aria-hidden /> : null}
              <button
                type="button"
                role="menuitem"
                tabIndex={index === activeIndex ? 0 : -1}
                data-menu-index={index}
                className={`timeline-context-menu-item${action.danger ? ' is-danger' : ''}`}
                disabled={action.disabled}
                onFocus={() => setActiveIndex(index)}
                onClick={() => {
                  if (!action.disabled) {
                    action.onSelect()
                    onClose()
                  }
                }}
              >
                {Icon ? <Icon aria-hidden size={15} strokeWidth={1.8} /> : <span className="timeline-context-menu-icon-spacer" aria-hidden />}
                <span>{action.label}</span>
                {action.shortcut ? <kbd>{action.shortcut}</kbd> : null}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
