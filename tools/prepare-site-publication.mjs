// Fallback for installations where Sites' bundled workflow script is unavailable.
// Short-lived credentials are read from stdin and kept only in child-process env.
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import readline from 'node:readline'

if (process.stdin.isTTY) process.stdin.setRawMode(true)
console.log('Ready for publication JSON on stdin (input is hidden).')
const line = await new Promise(resolveLine => {
  const rl = readline.createInterface({ input: process.stdin, terminal: false })
  rl.once('line', value => { rl.close(); resolveLine(value) })
})
const { credential, archivePath } = JSON.parse(line)
if (process.stdin.isTTY) process.stdin.setRawMode(false)
const root = process.cwd()
const manifest = JSON.parse(readFileSync('.openai/hosting.json', 'utf8'))
const env = { ...process.env, GIT_TERMINAL_PROMPT: '0' }
const git = process.env.ODIN_GIT_EXECUTABLE || 'git'
function run(executable, args, extraEnv = {}) {
  const r = spawnSync(executable, args, { cwd: root, env: { ...env, ...extraEnv }, encoding: 'utf8', windowsHide: true, maxBuffer: 4 * 1024 * 1024 })
  if (r.status !== 0) throw new Error((r.stderr || r.stdout || r.error?.message || 'Command failed').replaceAll(credential.token, '[redacted]'))
  return r.stdout.trim()
}
if (!existsSync('.git')) run(git, ['init', '-b', credential.branch])
const remoteNames = run(git, ['remote']).split('\n')
if (remoteNames.includes('sites')) run(git, ['remote', 'set-url', 'sites', credential.remote_url])
else run(git, ['remote', 'add', 'sites', credential.remote_url])
run(git, ['add', 'app', 'public', 'tools', 'nuxt.config.ts', 'package.json', 'package-lock.json', 'README.md', '.gitignore', '.nvmrc', '.openai/hosting.json', '启动预览.ps1'])
const staged = run(git, ['diff', '--cached', '--name-only'])
if (staged) run(git, ['-c', 'user.name=Codex', '-c', 'user.email=codex@openai.com', 'commit', '-m', 'Build Nuxt Odin fan-art showcase with runtime 3D animation'])
const commit = run(git, ['rev-parse', 'HEAD'])
run(git, ['push', 'sites', `HEAD:${credential.branch}`], {
  GIT_CONFIG_COUNT: '1', GIT_CONFIG_KEY_0: 'http.extraHeader', GIT_CONFIG_VALUE_0: `Authorization: Bearer ${credential.token}`,
})
if (run(git, ['status', '--porcelain'])) throw new Error('Working tree changed during publication')
run('tar', ['-czf', resolve(archivePath), '.openai/hosting.json', '.output/public'])
const entries = run('tar', ['-tzf', resolve(archivePath)]).split(/\r?\n/)
if (!entries.includes('.output/public/index.html') || entries.some(e => e.includes('node_modules/') || e.includes('work/'))) throw new Error('Invalid deployment archive')
console.log(JSON.stringify({ project_id: manifest.project_id, checkout_path: root, commit_sha: commit, archive: resolve(archivePath) }))
