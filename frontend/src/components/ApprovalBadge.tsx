interface ApprovalBadgeProps {
  approverRole?: string | null
}

export default function ApprovalBadge({ approverRole }: ApprovalBadgeProps) {
  const role = approverRole ?? 'Crew Chief'

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
                 bg-yellow-500/10 border border-yellow-500/30
                 text-yellow-400 text-xs font-medium"
    >
      {/* Shield icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="w-3.5 h-3.5"
      >
        <path
          fillRule="evenodd"
          d="M9.661 2.237a.531.531 0 01.678 0 11.947 11.947 0 007.078 2.749.5.5 0 01.479.578 12.047 12.047 0 01-8.916 10.425.532.532 0 01-.56-.11A12.046 12.046 0 012.06 5.564a.5.5 0 01.479-.578A11.947 11.947 0 009.66 2.237z"
          clipRule="evenodd"
        />
      </svg>
      {role} Approval Required
    </span>
  )
}
