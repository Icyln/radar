export function EmptyState({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return (
    <div className="panel px-6 py-12 text-center">
      <div className="mx-auto grid h-10 w-10 place-items-center rounded-full border border-zinc-800 bg-zinc-900 text-zinc-500">•</div>
      <h2 className="mt-4 text-sm font-semibold text-zinc-100">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-zinc-500">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
