import { useEffect, useState } from 'react';

import { get } from '../api/client';
import type { SessionResponse } from '../api/types';

export function useSession(sessionId: string | null) {
  const [data, setData] = useState<SessionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    let isMounted = true;
    setLoading(true);
    get<SessionResponse>(`/metadata/sessions/${sessionId}`)
      .then((response) => {
        if (!isMounted) return;
        setData(response);
        setError(null);
      })
      .catch((err: Error) => {
        if (!isMounted) return;
        setError(err);
      })
      .finally(() => {
        if (!isMounted) return;
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [sessionId]);

  return { data, loading, error };
}
