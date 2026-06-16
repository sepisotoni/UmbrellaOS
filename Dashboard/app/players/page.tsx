import { PageHeader } from '@/components/page-header'
import { PlayersTable } from '@/components/players/players-table'

export default function PlayersPage() {
  return (
    <>
      <PageHeader
        title="Players"
        description="Every account known to the network, with risk scoring and identity intelligence."
      />
      <PlayersTable />
    </>
  )
}
