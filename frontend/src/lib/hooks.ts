import { useCallback, useEffect, useRef, useState } from "react";

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const loaderRef = useRef(loader);
  loaderRef.current = loader;
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: true,
    error: null,
  });
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const reload = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const data = await loaderRef.current();
      if (mounted.current) setState({ data, loading: false, error: null });
    } catch (error) {
      if (mounted.current) {
        setState({ data: null, loading: false, error: error as Error });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { ...state, reload, setData: (data: T) => setState({ data, loading: false, error: null }) };
}

export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = `${title} · ClassMind AI`;
  }, [title]);
}
