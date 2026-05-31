import { cpSync, mkdirSync, rmSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"
import { build } from "esbuild"

const root = join(dirname(fileURLToPath(import.meta.url)), "..")
const lexxyPackage = join(root, "node_modules/@37signals/lexxy")
const staticLexxy = join(root, "prose/static/prose/lexxy")
const stylesheetNames = [
  "lexxy-variables.css",
  "lexxy-content.css",
  "lexxy-editor.css",
]

await build({
  entryPoints: [join(lexxyPackage, "dist/lexxy.esm.js")],
  outfile: join(staticLexxy, "lexxy.esm.js"),
  bundle: true,
  format: "esm",
  minify: true,
  external: ["@rails/activestorage"],
})

mkdirSync(join(staticLexxy, "stylesheets"), { recursive: true })
for (const name of stylesheetNames) {
  cpSync(
    join(lexxyPackage, "dist/stylesheets", name),
    join(staticLexxy, "stylesheets", name)
  )
}

console.log("Vendored @37signals/lexxy into prose/static/prose/lexxy/")
