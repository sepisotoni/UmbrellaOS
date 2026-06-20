export default function NoAccessPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-3xl font-bold">Access Denied</h1>
        <p className="text-muted-foreground">You don't have permission to access this dashboard.</p>
        <p className="text-sm text-muted-foreground">Contact a server administrator to get access.</p>
      </div>
    </div>
  )
}
