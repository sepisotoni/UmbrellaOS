import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'

// Deterministic accent color derived from the username for the fallback tile.
function hueFromString(s: string) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360
  return h
}

export function PlayerAvatar({
  username,
  uuid,
  className,
}: {
  username: string
  uuid: string
  className?: string
}) {
  const hue = hueFromString(username)
  return (
    <Avatar className={cn('rounded-md', className)}>
      <AvatarImage
        src={`https://mc-heads.net/avatar/${uuid}/64`}
        alt={`${username} skin head`}
        className="rounded-md"
      />
      <AvatarFallback
        className="rounded-md text-xs font-semibold text-white"
        style={{ backgroundColor: `oklch(0.55 0.13 ${hue})` }}
      >
        {username.slice(0, 2).toUpperCase()}
      </AvatarFallback>
    </Avatar>
  )
}
