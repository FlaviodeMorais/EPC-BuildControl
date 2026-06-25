import { NavLink } from 'react-router-dom'
import clsx from 'clsx'

const NAV = [
  { to: '/dashboard',  label: 'Dashboard',  icon: '▦' },
  { to: '/spools',     label: 'Spools',     icon: '⊡' },
  { to: '/joints',     label: 'Juntas',     icon: '⊗' },
  { to: '/mto',        label: 'MTO',        icon: '≡' },
  { to: '/valves',     label: 'Válvulas',   icon: '⊕' },
  { to: '/uploads',    label: 'Importar',   icon: '↑' },
]

export default function Sidebar() {
  return (
    <aside className="w-56 min-h-screen bg-gray-900 text-gray-100 flex flex-col">
      <div className="px-4 py-5 border-b border-gray-700">
        <p className="text-xs text-gray-400 uppercase tracking-widest">Piping CMS</p>
        <p className="text-sm font-semibold mt-0.5">UGH · TOYO</p>
      </div>
      <nav className="flex-1 py-4">
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => clsx(
              'flex items-center gap-3 px-4 py-2.5 text-sm transition-colors',
              isActive
                ? 'bg-blue-600 text-white font-medium'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
            )}
          >
            <span className="text-base w-5 text-center">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-gray-700 text-xs text-gray-500">
        v0.1.0
      </div>
    </aside>
  )
}
