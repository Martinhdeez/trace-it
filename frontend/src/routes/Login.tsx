import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { Button, Field, Input } from '../components/shell/Controls'
import { ErrorNotice } from '../components/shell/Notice'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { paths } from '../lib/paths'
import { useSession } from '../state/session'

export function Login() {
  const { user, signIn } = useSession()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')

  const login = useMutation({
    mutationFn: () => signIn(email.trim()),
    onSuccess: () => navigate(paths.processes, { replace: true }),
  })

  if (user && !login.isPending) return <Navigate to={paths.processes} replace />

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (email.trim()) login.mutate()
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
      <PageIntro
        kicker="trace.it"
        title="Entrar"
        description="Tu email identifica a quién se le atribuye cada decisión. Solo un responsable puede resolver casos y publicar."
      />
      <form onSubmit={submit} className="max-w-2xl space-y-3">
        <NestedCard label="usuario">
          <div className="space-y-3 px-3.5 py-3">
            <Field label="Email">
              <Input
                type="email"
                autoFocus
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="martin@trace-it.local"
              />
            </Field>
            {login.isError ? <ErrorNotice error={login.error} /> : null}
            <Button tone="primary" type="submit" disabled={!email.trim() || login.isPending}>
              Entrar
            </Button>
          </div>
        </NestedCard>
      </form>
    </div>
  )
}
