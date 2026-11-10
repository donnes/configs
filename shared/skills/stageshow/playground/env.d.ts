// Stands in for vite/client: vp brings its own Vite, so none is installed here.
declare module '*.css'
declare module '*.jpg' { const url: string; export default url }
declare module '*.png' { const url: string; export default url }
declare module '*.svg' { const url: string; export default url }
interface ImportMeta {
  glob<T = unknown>(pattern: string): Record<string, () => Promise<T>>
}
