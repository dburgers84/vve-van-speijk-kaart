# Werken met branches

- **`main`** — bron voor live site
- **`dev`** — doorontwikkeling; wijzigingen via pull request naar `main`
- **`gh-pages`** — gegenereerde site (niet handmatig editen)

## Live & preview
- Live (`main`): https://dburgers84.github.io/vve-van-speijk-kaart/
- Preview (`dev`): https://dburgers84.github.io/vve-van-speijk-kaart/dev/

Na pushes naar `dev` of `main` vernieuwen we `gh-pages` (live + /dev/).

## Flow
1. Werk op `dev`.
2. Open/update PR `dev` → `main`.
3. Na merge: live URL bijwerken via `gh-pages`.
