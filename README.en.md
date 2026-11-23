<p align="center">
  <a href="README.md">Español</a> · <b>English</b>
</p>

# modelos·al·día

**ChatGPT (OpenAI), Claude (Anthropic), Gemini (Google) and Grok (xAI, now part of SpaceX), compared
and up to date.** Models, API prices, capabilities, app plans, coding agents (Claude Code, Codex,
Antigravity, Copilot, Cursor and more) and each company's official release notes. Every data point
links to its source; anything unconfirmed is tagged.

**Site:** [beg-lag.github.io/modelos-al-dia](https://beg-lag.github.io/modelos-al-dia/) (Spanish) ·
**Tables:** [`TABLAS.md`](TABLAS.md) · **Data:** [`data/`](data)

## How it stays current

1. **Automatic, twice a day** (GitHub Actions): the model catalog from [models.dev](https://models.dev)
   and the public [OpenRouter](https://openrouter.ai) model list, the four providers' API release notes,
   product blogs, and GitHub releases of the open-source coding agents. No API keys needed. Changes
   between runs (new models, retirements, price and context changes) are logged in `data/cambios.json`.
2. **Curated** in `data/curado/*.yaml`: plans, capabilities, featured models per category and coding
   agents, each with a source URL and verification date.
3. **Weekly review**: a Claude workflow checks the week's news against official sources, edits the
   curated files and opens a pull request. Nothing is published without human approval.

Code under [MIT](LICENSE); original data under [CC0](DATA-LICENSE.md). Independent project, not
affiliated with OpenAI, Anthropic, Google or xAI/SpaceX.
