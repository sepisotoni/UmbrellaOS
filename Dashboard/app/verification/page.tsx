'use client'

import { toast } from 'sonner'
import { usePendingVerifications, useRevokeVerification } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { timeAgo } from '@/lib/format'
import type { VerificationCode } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export default function VerificationPage() {
  const { data, isLoading } = usePendingVerifications()
  const revokeVerification = useRevokeVerification()

  const handleRevoke = async (player_uuid: string) => {
    try {
      await revokeVerification.mutateAsync(player_uuid)
      toast.success('Verification revoked')
    } catch (error) {
      toast.error('Failed to revoke verification')
    }
  }

  return (
    <>
      <PageHeader
        title="Verification"
        description="Manage player verification codes for Discord-based authentication."
      />

      {isLoading ? (
        <Card>
          <CardContent className="p-6">
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-6">
            {data && data.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Username</TableHead>
                    <TableHead>UUID</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>Requested At</TableHead>
                    <TableHead>Expires At</TableHead>
                    <TableHead>IP</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((code: VerificationCode) => (
                    <TableRow key={code.id}>
                      <TableCell className="font-medium">{code.player_username}</TableCell>
                      <TableCell className="font-mono text-xs">{code.player_uuid}</TableCell>
                      <TableCell className="font-mono font-bold">{code.code}</TableCell>
                      <TableCell>{timeAgo(code.created_at)}</TableCell>
                      <TableCell>{timeAgo(code.expires_at)}</TableCell>
                      <TableCell className="font-mono text-xs">{code.ip_address || '-'}</TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleRevoke(code.player_uuid)}
                        >
                          Revoke
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="py-10 text-center text-sm text-muted-foreground">
                No pending verifications.
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </>
  )
}
