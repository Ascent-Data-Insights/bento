import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { branding } from '../config/branding'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleLogin = () => {
    login()
    navigate('/')
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm rounded-xl bg-white p-8 shadow-lg ring-1 ring-gray-950/5">
        <div className="flex flex-col items-center gap-4">
          <img src={branding.logo} alt={branding.company} className="h-16" />
          <h1 className="font-heading text-2xl font-semibold text-brand-primary">
            {branding.name}
          </h1>
          <p className="text-sm text-gray-500">
            by {branding.company}
          </p>
        </div>
        <div className="mt-8">
          <button
            onClick={handleLogin}
            className="w-full rounded-lg bg-brand-accent px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-accent/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-accent transition"
          >
            Sign In
          </button>
        </div>
      </div>
    </div>
  )
}
