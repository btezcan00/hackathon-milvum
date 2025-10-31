import { useEffect, useState } from 'react';

/**
 * Hook to determine if we're running on the client side.
 * Prevents hydration mismatches by returning false during SSR.
 */
export function useClientOnly() {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return isClient;
}
