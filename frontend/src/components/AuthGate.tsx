'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';

import { useAuth } from '@/components/AuthProvider';

type AuthGateProps = {
  children: React.ReactNode;
  roles?: string[];
};

export default function AuthGate({ children, roles }: AuthGateProps) {
  const { isLoading, isAuthenticated, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (isLoading) {
      return;
    }

    if (!isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }

    if (roles && user && !roles.includes(user.user_group)) {
      router.replace('/');
    }
  }, [isAuthenticated, isLoading, pathname, roles, router, user]);

  if (
    isLoading ||
    !isAuthenticated ||
    (roles && user && !roles.includes(user.user_group))
  ) {
    return <div className="py-20 text-center text-sm text-gray-500">Checking session...</div>;
  }

  return <>{children}</>;
}
