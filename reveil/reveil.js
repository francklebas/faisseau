// Worker Cloudflare : à chaque cron, déclenche le workflow quotidien du dépôt GitHub.
export default {
  async scheduled(evenement, env, ctx) {
    ctx.waitUntil(reveiller(env, evenement.cron));
  },
  // Aucune page : le Worker n'a pas d'adresse publique (workers_dev désactivé).
  async fetch() {
    return new Response("Rien ici.", { status: 404 });
  },
};

async function reveiller(env, cron) {
  if (!env.GITHUB_TOKEN) throw new Error("Secret GITHUB_TOKEN absent (wrangler secret put GITHUB_TOKEN)");
  const reponse = await fetch(`https://api.github.com/repos/${env.DEPOT}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "revue-du-matin-reveil",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ event_type: "revue-du-matin", client_payload: { cron } }),
  });
  // 204 : GitHub a pris la demande. Toute autre réponse fait échouer l'exécution, visible
  // dans le tableau de bord Cloudflare (Workers → revue-du-matin-reveil → Logs).
  if (reponse.status !== 204) {
    throw new Error(`GitHub a répondu ${reponse.status} : ${await reponse.text()}`);
  }
  console.log(`Workflow quotidien demandé (cron ${cron})`);
}
