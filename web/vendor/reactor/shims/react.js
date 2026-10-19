// AUTHORED shim (not React): this bundle uses only the SDK's imperative Reactor class. The SDK module
// calls createContext once at load; every hook refuses if a React component is ever rendered.
const refuse = (n) => () => { throw new Error('React is not bundled here (' + n + '); use the imperative Reactor class'); };
export const createContext = (v) => ({ _currentValue: v, Provider: null, Consumer: null });
export const useContext = refuse('useContext');
export const useEffect = refuse('useEffect');
export const useRef = refuse('useRef');
export const useState = refuse('useState');
export const useMemo = refuse('useMemo');
export const useCallback = refuse('useCallback');
export const useSyncExternalStore = refuse('useSyncExternalStore');
export default { createContext };
