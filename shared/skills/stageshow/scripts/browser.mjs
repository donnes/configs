// The headless browser the filming scripts share. playwright-core is the one
// dependency filming needs and the kit doesn't, so a missing install says how
// to fix it rather than failing on the import. Chrome is the installed one
// (CHROME_PATH overrides), found on macOS, Windows and Linux alike, with
// Helium as the fallback.
const HELIUM = process.platform === 'darwin' ? '/Applications/Helium.app/Contents/MacOS/Helium' : '/usr/bin/helium-browser'

export async function launch() {
  let chromium
  try {
    ;({ chromium } = await import('playwright-core'))
  } catch {
    console.error('Filming needs playwright-core: run `vp add -D playwright-core` in this project, then try again.')
    process.exit(2)
  }
  const path = process.env.CHROME_PATH
  const attempts = path ? [{ executablePath: path }] : [{ channel: 'chrome' }, { executablePath: HELIUM }]
  for (const options of attempts) {
    try {
      return await chromium.launch(options)
    } catch {}
  }
  console.error(`Couldn't start Chrome${path ? ` at ${path}` : ' or Helium'}. Install Google Chrome, or set CHROME_PATH to a Chrome or Chromium binary.`)
  process.exit(2)
}
