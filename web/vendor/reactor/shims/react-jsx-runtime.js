// AUTHORED shim (not React): JSX is never rendered in this bundle.
const refuse = () => { throw new Error('React JSX is not bundled here; use the imperative Reactor class'); };
export const jsx = refuse;
export const jsxs = refuse;
export const Fragment = null;
