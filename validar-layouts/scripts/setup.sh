#!/bin/bash
# setup.sh: prepara as FERRAMENTAS externas em /tmp/vl-tools (Hallmark, ui-ux-pro-max, Tailwind, puppeteer-core e um
# wrapper do Chrome). Os scripts da skill ficam aqui em scripts/ e não são copiados. Uso: bash <SKILL>/scripts/setup.sh
T=${VL_TOOLS:-/tmp/vl-tools}; mkdir -p "$T" && cd "$T" || exit 1
[ -d hallmark ] || git clone -q --depth 1 https://github.com/Nutlope/hallmark.git hallmark
[ -d uupm ] || git clone -q --depth 1 https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git uupm
[ -f package.json ] || npm init -y >/dev/null
[ -d node_modules/puppeteer-core ] || npm i -s tailwindcss@3 @tailwindcss/forms @tailwindcss/typography \
  @tailwindcss/aspect-ratio @tailwindcss/container-queries puppeteer-core@23.11.1 >/dev/null 2>&1
# Chrome: o do Playwright se existir; senão o Google Chrome instalado no sistema
CH=$(python3 -c "from playwright.sync_api import sync_playwright as s
with s() as p: print(p.chromium.executable_path)" 2>/dev/null)
if [ -z "$CH" ] || [ ! -x "$CH" ]; then CH=$(command -v google-chrome || command -v chromium || command -v chromium-browser); fi
[ -n "$CH" ] || { echo "FALTA: Chrome/Chromium (instale ou rode: python3 -m playwright install chromium)"; exit 1; }
printf '#!/bin/sh\nexec "%s" --no-sandbox "$@"\n' "$CH" > "$T/chrome" && chmod +x "$T/chrome"
python3 -c "import playwright, PIL" 2>/dev/null || echo "FALTA: pip install playwright pillow"
echo "hallmark $(git -C hallmark rev-parse --short HEAD) | ui-ux-pro-max $(git -C uupm rev-parse --short HEAD)"
ls node_modules/.bin/tailwindcss node_modules/puppeteer-core/package.json >/dev/null && echo ok
