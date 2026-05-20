export function LoadingSkeleton() {
  return (
    <div className="grid gap-3">
      <div className="h-5 w-2/5 animate-pulse rounded-full bg-mist" />
      <div className="h-20 animate-pulse rounded-3xl bg-mist" />
      <div className="h-20 animate-pulse rounded-3xl bg-mist" />
      <div className="h-20 animate-pulse rounded-3xl bg-mist" />
    </div>
  );
}
