import { useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useTenant } from '../contexts/TenantContext'
import { useTour } from '../contexts/TourContext'
import { branding } from '../config/branding'
import { SidebarLayout, useSidebarCollapse, useMobileSidebar } from '../components/sidebar-layout'
import {
  Sidebar,
  SidebarBody,
  SidebarFooter,
  SidebarHeader,
  SidebarItem,
  SidebarLabel,
  SidebarSection,
} from '../components/sidebar'
import { Navbar, NavbarItem, NavbarSpacer } from '../components/navbar'
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
    tourId: undefined,
    icon: (
      <svg data-slot="icon" viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path fillRule="evenodd" d="M9.293 2.293a1 1 0 0 1 1.414 0l7 7A1 1 0 0 1 17 11h-1v6a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1v-3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-6H3a1 1 0 0 1-.707-1.707l7-7Z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    label: 'Crew Schedule',
    href: '/crew',
    tourId: 'crew-schedule-nav',
    icon: (
      <svg data-slot="icon" viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M7 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM14.5 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM1.615 16.428a1.224 1.224 0 0 1-.569-1.175 6.002 6.002 0 0 1 11.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 0 1 7 17a9.953 9.953 0 0 1-5.385-1.572ZM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 0 0-1.588-3.755 4.502 4.502 0 0 1 5.874 2.636.818.818 0 0 1-.36.98A7.465 7.465 0 0 1 14.5 16Z" />
      </svg>
    ),
  },
  {
    label: 'New Tenant',
    href: '/onboard',
    tourId: 'onboard-nav',
    icon: (
      <svg data-slot="icon" viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
      </svg>
    ),
  },
  {
    label: 'Data Entry',
    href: '/data',
    tourId: 'data-entry-nav',
    icon: (
      <svg data-slot="icon" viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path fillRule="evenodd" d="M.99 5.24A2.25 2.25 0 0 1 3.25 3h13.5A2.25 2.25 0 0 1 19 5.25l.01 9.5A2.25 2.25 0 0 1 16.76 17H3.26A2.272 2.272 0 0 1 1 14.75l-.01-9.5Zm8.26 9.52v-.001a.75.75 0 0 0 1.5 0v-5.19l1.72 1.72a.75.75 0 1 0 1.06-1.06L10.53 7.23a.75.75 0 0 0-1.06 0L6.47 10.23a.75.75 0 1 0 1.06 1.06l1.72-1.72v5.19Z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    label: 'Admin',
    href: '/admin',
    tourId: undefined,
    icon: (
      <svg data-slot="icon" viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path fillRule="evenodd" d="M7.84 1.804A1 1 0 0 1 8.82 1h2.36a1 1 0 0 1 .98.804l.331 1.652a6.993 6.993 0 0 1 1.929 1.115l1.598-.54a1 1 0 0 1 1.186.447l1.18 2.044a1 1 0 0 1-.205 1.251l-1.267 1.113a7.047 7.047 0 0 1 0 2.228l1.267 1.113a1 1 0 0 1 .205 1.251l-1.18 2.044a1 1 0 0 1-1.186.447l-1.598-.54a6.993 6.993 0 0 1-1.929 1.115l-.33 1.652a1 1 0 0 1-.98.804H8.82a1 1 0 0 1-.98-.804l-.331-1.652a6.993 6.993 0 0 1-1.929-1.115l-1.598.54a1 1 0 0 1-1.186-.447l-1.18-2.044a1 1 0 0 1 .205-1.251l1.267-1.113a7.047 7.047 0 0 1 0-2.228L1.821 7.773a1 1 0 0 1-.205-1.251l1.18-2.044a1 1 0 0 1 1.186-.447l1.598.54A6.992 6.992 0 0 1 7.51 3.456l.33-1.652ZM10 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" clipRule="evenodd" />
      </svg>
    ),
  },
]

function HelpIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
      <path fillRule="evenodd" d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z" clipRule="evenodd" />
    </svg>
  )
}

function AppSidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout } = useAuth()
  const { collapsed } = useSidebarCollapse()
  const { tenants, activeTenant, setActiveTenant } = useTenant()
  const { start } = useTour()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <Sidebar>
      {collapsed ? (
        <SidebarHeader>
          <div className="flex justify-center px-2">
            <span className="font-heading text-lg font-bold text-brand-primary">
              {activeTenant?.name?.[0] || 'B'}
            </span>
          </div>
        </SidebarHeader>
      ) : (
        <SidebarHeader>
          <Dropdown>
            <DropdownButton
              as="button"
              data-tour="tenant-selector"
              className="flex items-center gap-2 px-2 w-full text-left rounded-lg hover:bg-zinc-950/5 py-2 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="font-heading text-sm font-semibold text-brand-primary leading-tight">
                  {activeTenant?.name || branding.name}
                </div>
              </div>
              <svg className="w-4 h-4 text-gray-400 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
              </svg>
            </DropdownButton>
            <DropdownMenu anchor="bottom start" className="min-w-[240px]">
              {tenants.map((t) => (
                <DropdownItem key={t.id} onClick={() => setActiveTenant(t)}>
                  <div>
                    <div className="font-medium text-sm">{t.name}</div>
                    <div className="text-xs text-gray-500">{t.industry}</div>
                  </div>
                </DropdownItem>
              ))}
            </DropdownMenu>
          </Dropdown>
        </SidebarHeader>
      )}
      <SidebarBody>
        <SidebarSection>
          {navItems.map((item) => (
            <span key={item.href} data-tour={item.tourId ?? undefined}>
              <SidebarItem
                href={item.href}
                current={location.pathname === item.href}
              >
                {item.icon}
                {!collapsed && <SidebarLabel>{item.label}</SidebarLabel>}
              </SidebarItem>
            </span>
          ))}
        </SidebarSection>
      </SidebarBody>
      <SidebarFooter>
        {/* Tour trigger button */}
        <SidebarItem onClick={start} aria-label="Start guided tour">
          <HelpIcon />
          {!collapsed && <SidebarLabel>Take a tour</SidebarLabel>}
        </SidebarItem>
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

// Registers tour prepare handlers that need access to the mobile sidebar context,
// which is only available inside SidebarLayout. Renders nothing.
function TourPrepareRegistrar() {
  const { registerPrepareHandler } = useTour()
  const { setOpen } = useMobileSidebar()

  useEffect(() => {
    const unregSidebar = registerPrepareHandler('sidebar', () => setOpen(true))
    const unregClose = registerPrepareHandler('close-sidebar', () => setOpen(false))
    return () => {
      unregSidebar()
      unregClose()
    }
  }, [registerPrepareHandler, setOpen])

  return null
}

export function AppLayout() {
  const location = useLocation()
  const { start } = useTour()
  const fullBleedPaths = ['/']
  const isFullBleed = fullBleedPaths.includes(location.pathname)

  return (
    <SidebarLayout
      navbar={
        <Navbar>
          <NavbarSpacer />
          <NavbarItem onClick={start} aria-label="Start guided tour">
            <HelpIcon />
          </NavbarItem>
        </Navbar>
      }
      sidebar={<AppSidebar />}
      fullBleed={isFullBleed}
    >
      <TourPrepareRegistrar />
      <Outlet />
    </SidebarLayout>
  )
}
