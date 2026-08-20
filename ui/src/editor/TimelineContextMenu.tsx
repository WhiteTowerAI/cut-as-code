import { useEffect, useLayoutEffect, useRef, useState, type ComponentType, type MouseEvent as ReactMouseEvent } from 'react'
import { ChevronRight } from 'lucide-react'

export type TimelineContextMenuAction = Readonly<{
  id: string
  label: string
  shortcut?: string
  icon?: ComponentType<{ 'aria-hidden'?: boolean; size?: number; strokeWidth?: number }>
  disabled?: boolean
  danger?: boolean
  separatorBefore?: boolean
  submenu?: readonly TimelineContextMenuAction[]
  onSelect?: () => void
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
  const [openSubmenuId, setOpenSubmenuId] = useState<string | null>(null)
  const [activeSubmenuIndex, setActiveSubmenuIndex] = useState(-1)

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
    const active = activeSubmenuIndex >= 0
      ? menu.querySelector<HTMLElement>(`[data-submenu-index="${activeSubmenuIndex}"]`)
      : activeIndex >= 0
        ? menu.querySelector<HTMLElement>(`[data-menu-index="${activeIndex}"]`)
        : null
    active?.focus()
  }, [activeIndex, activeSubmenuIndex])

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
        const submenu = actions.find((action) => action.id === openSubmenuId)?.submenu
        if (submenu && activeSubmenuIndex >= 0) {
          setActiveSubmenuIndex((current) => nextEnabled(submenu, current, event.key === 'ArrowDown' ? 1 : -1))
        } else {
          setActiveIndex((current) => nextEnabled(actions, current, event.key === 'ArrowDown' ? 1 : -1))
        }
        return
      }
      if (event.key === 'ArrowRight') {
        const action = actions[activeIndex]
        if (action?.submenu?.length) {
          event.preventDefault()
          setOpenSubmenuId(action.id)
          setActiveSubmenuIndex(nextEnabled(action.submenu, -1, 1))
        }
        return
      }
      if (event.key === 'ArrowLeft' && openSubmenuId) {
        event.preventDefault()
        setOpenSubmenuId(null)
        setActiveSubmenuIndex(-1)
        return
      }
      if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault()
        const submenu = actions.find((action) => action.id === openSubmenuId)?.submenu
        if (submenu && activeSubmenuIndex >= 0) {
          const indexes = enabledIndexes(submenu)
          setActiveSubmenuIndex(indexes.length ? (event.key === 'Home' ? indexes[0] : indexes.at(-1)!) : -1)
        } else {
          const indexes = enabledIndexes(actions)
          setActiveIndex(indexes.length ? (event.key === 'Home' ? indexes[0] : indexes.at(-1)!) : -1)
        }
        return
      }
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        const submenu = actions.find((action) => action.id === openSubmenuId)?.submenu
        if (submenu && activeSubmenuIndex >= 0) {
          const child = submenu[activeSubmenuIndex]
          if (child && !child.disabled) {
            child.onSelect?.()
            onClose()
          }
          return
        }
        const action = actions[activeIndex]
        if (activeIndex >= 0 && action && !action.disabled) {
          if (action.submenu?.length) setOpenSubmenuId(action.id)
          else {
            action.onSelect?.()
            onClose()
          }
        }
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [actions, activeIndex, activeSubmenuIndex, onClose, openSubmenuId])

  const submenuOpensLeft = position.left + 276 + 4 + 248 > window.innerWidth - 8

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
          const submenuOpen = openSubmenuId === action.id && Boolean(action.submenu?.length)
          return (
            <div key={action.id} className={`timeline-context-menu-action${action.separatorBefore ? ' timeline-context-menu-separator' : ''}`}>
              <button
                type="button"
                role="menuitem"
                aria-haspopup={action.submenu?.length ? 'menu' : undefined}
                aria-expanded={action.submenu?.length ? submenuOpen : undefined}
                tabIndex={index === activeIndex ? 0 : -1}
                data-menu-index={index}
                className={`timeline-context-menu-item${action.danger ? ' is-danger' : ''}`}
                disabled={action.disabled}
                onFocus={() => setActiveIndex(index)}
                onMouseEnter={() => action.submenu?.length && setOpenSubmenuId(action.id)}
                onClick={() => {
                  if (action.disabled) return
                  if (action.submenu?.length) setOpenSubmenuId(action.id)
                  else {
                    action.onSelect?.()
                    onClose()
                  }
                }}
              >
                {Icon ? <Icon aria-hidden size={15} strokeWidth={1.8} /> : <span className="timeline-context-menu-icon-spacer" aria-hidden />}
                <span>{action.label}</span>
                {action.shortcut ? <kbd>{action.shortcut}</kbd> : null}
                {action.submenu?.length ? <ChevronRight aria-hidden size={14} strokeWidth={1.8} /> : null}
              </button>
              {submenuOpen && action.submenu ? (
                <div className={`timeline-context-submenu${submenuOpensLeft ? ' opens-left' : ''}`} role="menu" aria-label={action.label}>
                  {action.submenu.map((child, childIndex) => {
                    const ChildIcon = child.icon
                    return (
                      <button
                        key={child.id}
                        type="button"
                        role="menuitem"
                        tabIndex={childIndex === activeSubmenuIndex ? 0 : -1}
                        data-submenu-index={childIndex}
                        className={`timeline-context-menu-item${child.danger ? ' is-danger' : ''}`}
                        disabled={child.disabled}
                        onFocus={() => setActiveSubmenuIndex(childIndex)}
                        onClick={() => {
                          if (!child.disabled) {
                            child.onSelect?.()
                            onClose()
                          }
                        }}
                      >
                        {ChildIcon ? <ChildIcon aria-hidden size={15} strokeWidth={1.8} /> : <span className="timeline-context-menu-icon-spacer" aria-hidden />}
                        <span>{child.label}</span>
                        {child.shortcut ? <kbd>{child.shortcut}</kbd> : null}
                      </button>
                    )
                  })}
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
