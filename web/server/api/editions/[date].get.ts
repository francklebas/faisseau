export default defineEventHandler(async event => resumer(await lireEdition(getRouterParam(event, 'date') ?? '')))
