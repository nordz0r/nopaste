# Local webfonts

This directory is used for local webfont files loaded by the UI:

- `inter-400.woff2`
- `inter-500.woff2`
- `inter-600.woff2`
- `jetbrains-mono-400.woff2`

## How to add fonts (without committing binaries)

Run from repository root:

```bash
./fetch_fonts.sh
```

This downloads the required `.woff2` files into `src/static/fonts/`.

## Upstream sources

- Inter: https://github.com/rsms/inter (`docs/font-files/*.woff2`)
- JetBrains Mono: https://github.com/JetBrains/JetBrainsMono (`fonts/webfonts/*.woff2`)

## Licenses

- `INTER-LICENSE.txt`
- `JETBRAINS-MONO-LICENSE.txt`
