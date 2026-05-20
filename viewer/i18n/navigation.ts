// Phase 6 i18n navigation — locked decision D-01 in 06-CONTEXT.md.
// Typed Link/redirect/usePathname/useRouter bound to the locked routing config.
// Source: https://next-intl.dev/docs/routing/navigation
import {createNavigation} from 'next-intl/navigation';
import {routing} from './routing';

export const {Link, redirect, usePathname, useRouter, getPathname} =
  createNavigation(routing);
