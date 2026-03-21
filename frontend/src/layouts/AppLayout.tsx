import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { branding } from '../config/branding'
import { SidebarLayout, useSidebarCollapse } from '../components/sidebar-layout'
import {
  Sidebar,
  SidebarBody,
  SidebarFooter,
  SidebarHeader,
  SidebarItem,
  SidebarLabel,
  SidebarSection,
} from '../components/sidebar'
import { Navbar, NavbarSpacer } from '../components/navbar'
import { Avatar } from '../components/avatar'
import {
  Dropdown,
  DropdownButton,
  DropdownMenu,
  DropdownItem,
} from '../components/dropdown'

const navItems = [
  {
    label: 'Dashboard',
    href: '/',
    icon: (
      <svg data-slot="icon" viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path fillRule="evenodd" d="M9.293 2.293a1 1 0 0 1 1.414 0l7 7A1 1 0 0 1 17 11h-1v6a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1v-3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-6H3a1 1 0 0 1-.707-1.707l7-7Z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    label: 'Routes',
    href: '/routes',
    icon: (
      <svg data-slot="icon" viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path fillRule="evenodd" d="m9.69 18.933.003.001C9.89 19.02 10 19 10 19s.11.02.308-.066l.002-.001.006-.003.018-.008a5.741 5.741 0 0 0 .281-.14c.186-.096.446-.24.757-.433.62-.384 1.445-.966 2.274-1.765C15.302 14.988 17 12.493 17 9A7 7 0 1 0 3 9c0 3.492 1.698 5.988 3.355 7.584a13.731 13.731 0 0 0 2.273 1.765 11.842 11.842 0 0 0 .976.544l.062.029.018.008.006.003ZM10 11.25a2.25 2.25 0 1 0 0-4.5 2.25 2.25 0 0 0 0 4.5Z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    label: 'Fleet & Crew',
    href: '/fleet',
    icon: (
      <svg data-slot="icon" viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M6.5 3c-1.051 0-2.093.04-3.125.117A1.49 1.49 0 0 0 2 4.607V10.5h-.5a.5.5 0 0 0-.5.5v2a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2h6a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-2a.5.5 0 0 0-.5-.5H16V4.607a1.49 1.49 0 0 0-1.375-1.49A44.07 44.07 0 0 0 11.5 3h-5ZM4.5 13a.5.5 0 1 1 0-1 .5.5 0 0 1 0 1Zm9 0a.5.5 0 1 1 0-1 .5.5 0 0 1 0 1ZM4 6.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-9a.5.5 0 0 1-.5-.5v-3Z" />
      </svg>
    ),
  },
]

function AppSidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout } = useAuth()
  const { collapsed } = useSidebarCollapse()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <Sidebar>
      <SidebarHeader>
        {collapsed ? (
          <div className="flex justify-center px-2">
            <span className="font-heading text-lg font-bold text-brand-primary">B</span>
          </div>
        ) : (
          <div className="flex items-center gap-3 px-2">
            <img src={branding.logo} alt={branding.company} className="h-8" />
            <span className="font-heading text-lg font-semibold text-brand-primary">
              {branding.name}
            </span>
          </div>
        )}
      </SidebarHeader>
      <SidebarBody>
        <SidebarSection>
          {navItems.map((item) => (
            <SidebarItem
              key={item.href}
              href={item.href}
              current={location.pathname === item.href}
            >
              {item.icon}
              {!collapsed && <SidebarLabel>{item.label}</SidebarLabel>}
            </SidebarItem>
          ))}
        </SidebarSection>
      </SidebarBody>
      <SidebarFooter>
        <Dropdown>
          <DropdownButton as={SidebarItem}>
            <Avatar initials="JD" className="size-6 bg-brand-secondary text-white text-xs" />
            {!collapsed && <SidebarLabel>Jane Doe</SidebarLabel>}
          </DropdownButton>
          <DropdownMenu anchor="top start" className="min-w-48">
            <DropdownItem onClick={handleLogout}>
              <span>Sign out</span>
            </DropdownItem>
          </DropdownMenu>
        </Dropdown>
      </SidebarFooter>
    </Sidebar>
  )
}

export function AppLayout() {
  return (
    <SidebarLayout
      navbar={
        <Navbar>
          <NavbarSpacer />
        </Navbar>
      }
      sidebar={<AppSidebar />}
    >
      <Outlet />
    </SidebarLayout>
  )
}
