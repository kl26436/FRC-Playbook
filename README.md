# FRC-Playbook

The Team 4206 playbook site: how one robot, Robot A, went from kickoff analysis to design, manufacturing, assembly, wiring and code, written so students can repeat the process on a new game.

Live at https://kl26436.github.io/FRC-Playbook/

## How it works

- Pages are Markdown files in `src/content/docs/`. Edit one, push to `main`, and the site republishes in a few minutes.
- The sidebar order is set in `astro.config.mjs`.
- Built with [Astro](https://astro.build) and its [Starlight](https://starlight.astro.build) docs theme.
- `.github/workflows/deploy.yml` builds and publishes the site to GitHub Pages on every push to `main`.

## Run it on your computer

Needs Node.js 22 or newer.

```
npm install
npm run dev
```

Then open the address it prints.

## Connecting team.4206.rocks later

1. In this repo on GitHub: Settings, Pages, set the custom domain to `team.4206.rocks`.
2. At the domain registrar, add a DNS record: type CNAME, host `team`, value `kl26436.github.io`.
3. In `astro.config.mjs`, set `SITE` to `https://team.4206.rocks` and `BASE` to `/`, then push.
4. Back in Settings, Pages, turn on Enforce HTTPS once it is offered.
