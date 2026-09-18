import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { Button } from '../components/shell/Controls'
import { Empty, ErrorNotice } from '../components/shell/Notice'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { paths } from '../lib/paths'

export function Processes() {
  const processes = useQuery({ queryKey: keys.processes, queryFn: () => api.listProcesses() })

  return (
    <>
      <Topbar
        crumbs={[{ label: 'Procesos' }]}
        actions={
          <Link to={paths.newProcess}>
            <Button tone="primary">
              <Plus size={12} strokeWidth={2} />
              Nuevo proceso
            </Button>
          </Link>
        }
      />
      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker="Espacio"
          title="Procesos"
          description="Un proceso son unas reglas, un histórico de decisiones y las fuentes contra las que se validan. El pago de facturas es el primero, no el producto."
        />

        {processes.isError ? <ErrorNotice error={processes.error} /> : null}

        <NestedCard label={`${processes.data?.length ?? 0} procesos`}>
          {processes.data?.length ? (
            <ul className="divide-y divide-hairline">
              {processes.data.map((process) => (
                <li key={process.id}>
                  <Link to={paths.process(process.id)} className="block px-3.5 py-3 hover:bg-canvas">
                    <p className="text-[15px] font-medium">{process.nombre}</p>
                    <p className="mt-0.5 line-clamp-2 text-[12.5px] text-muted">
                      {process.descripcion}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>Ningún proceso todavía. Crea el primero o importa un JSON.</Empty>
          )}
        </NestedCard>
      </div>
    </>
  )
}
