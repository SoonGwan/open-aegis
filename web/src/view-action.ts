/** A response belongs to one visit, even when Back returns to the same URL. */
export class ViewScope {
  private revision = 0;

  invalidate() {
    this.revision++;
  }

  capture(): () => boolean {
    const revision = this.revision;
    return () => revision === this.revision;
  }
}

/** Persisted mutations must reconcile data even after the user leaves their view. */
export async function runViewAction<T>(options: {
  execute: () => Promise<T>;
  reconcile: () => Promise<void>;
  isCurrent: () => boolean;
  isSessionCurrent?: () => boolean;
  success: (value: T, current: boolean) => void;
  failure: (error: unknown, current: boolean) => void;
}): Promise<T | undefined> {
  const sessionCurrent = options.isSessionCurrent ?? (() => true);
  try {
    const value = await options.execute();
    if (!sessionCurrent()) return undefined;
    await options.reconcile();
    if (!sessionCurrent()) return undefined;
    const current = options.isCurrent();
    options.success(value, current);
    return current ? value : undefined;
  } catch (error) {
    if (sessionCurrent()) options.failure(error, options.isCurrent());
    return undefined;
  }
}
