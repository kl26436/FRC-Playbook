// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// The site is served from https://kl26436.github.io/FRC-Playbook/ for now.
// When team.4206.rocks is connected: set SITE to 'https://team.4206.rocks'
// and BASE to '/' (see README).
const SITE = 'https://kl26436.github.io';
const BASE = '/FRC-Playbook';

export default defineConfig({
  site: SITE,
  base: BASE,
  integrations: [
    starlight({
      title: 'Team 4206 Playbook',
      social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/kl26436/FRC-Playbook' }],
      sidebar: [
        {
                "label": "Start here",
                "slug": "start-here"
        },
        {
                "label": "1. Read the game",
                "slug": "read-the-game"
        },
        {
                "label": "2. Choose what to be good at",
                "slug": "choose-what-to-be-good-at"
        },
        {
                "label": "3. Concept",
                "slug": "concept"
        },
        {
                "label": "4. Subsystems",
                "items": [
                        {
                                "label": "Drivebase",
                                "slug": "subsystems/drivebase"
                        },
                        {
                                "label": "Elevator",
                                "slug": "subsystems/elevator"
                        },
                        {
                                "label": "Wrist and claw",
                                "slug": "subsystems/wrist-and-claw"
                        },
                        {
                                "label": "Funnel",
                                "slug": "subsystems/funnel"
                        },
                        {
                                "label": "Climber",
                                "slug": "subsystems/climber"
                        },
                        {
                                "label": "Bumpers",
                                "slug": "subsystems/bumpers"
                        },
                        {
                                "label": "Electronics",
                                "slug": "subsystems/electronics"
                        }
                ]
        },
        {
                "label": "5. Make it",
                "slug": "make-it"
        },
        {
                "label": "6. Assemble it",
                "slug": "assemble-it"
        },
        {
                "label": "7. Wire it",
                "slug": "wire-it"
        },
        {
                "label": "8. Code it",
                "slug": "code-it"
        },
        {
                "label": "9. Math reference",
                "slug": "math-reference"
        },
        {
                "label": "10. What went wrong",
                "slug": "what-went-wrong"
        },
        {
                "label": "11. Downloads",
                "slug": "downloads"
        }
],
    }),
  ],
});
