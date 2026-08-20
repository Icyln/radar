import Image from "next/image";
import Link from "next/link";

export function Brand({
  href = "/",
  subtitle = "Job alerts, simplified",
  compact = false,
  wordmark = false
}: {
  href?: string;
  subtitle?: string;
  compact?: boolean;
  wordmark?: boolean;
}) {
  if (wordmark) {
    return (
      <Link href={href} className="inline-flex items-center" aria-label="Radar home">
        <Image src="/radar-logo.png" alt="Radar" width={150} height={49} priority className="h-9 w-auto object-contain" />
      </Link>
    );
  }

  return (
    <Link href={href} className="inline-flex min-w-0 items-center gap-2.5" aria-label="Radar home">
      <Image
        src="/radar-mark.png"
        alt=""
        width={42}
        height={42}
        priority
        className={compact ? "h-8 w-8 shrink-0 object-contain" : "h-10 w-10 shrink-0 object-contain"}
      />
      <span className="min-w-0">
        <span className="block text-[15px] font-extrabold tracking-[-0.02em] text-main">Radar</span>
        {!compact ? (
          <span className="block truncate text-[9px] font-semibold uppercase tracking-[0.2em] text-faint">{subtitle}</span>
        ) : null}
      </span>
    </Link>
  );
}
