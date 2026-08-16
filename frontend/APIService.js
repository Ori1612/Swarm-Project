export class APIService {
    constructor() {
        this.baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? 'http://127.0.0.1:8000'
            : 'https://your-backend.onrender.com'; // No trailing slash
    }

    async fetchScenario(id, mode = 'both') {
        // Map scenario IDs to their correct time horizons (T)
        let T = 30;
        if (id === 'cyber_city') T = 75;
        else if (id === 'torture_track') T = 20;

        let modeStr = mode.toUpperCase();
        if (id === 'torture_track') {
            modeStr = 'BOTH';
        }

        const filename = `payload_${id}_${modeStr}_${T}.json`;

        // 1. First attempt: Load pre-calculated scenario JSON from static cache folder
        try {
            const cacheResponse = await fetch(`./cache_data/${filename}`, { cache: 'no-store' });
            if (cacheResponse.ok) {
                return await cacheResponse.json();
            }
            const fallbackCache = await fetch(`/cache_data/${filename}`, { cache: 'no-store' });
            if (fallbackCache.ok) {
                return await fallbackCache.json();
            }
        } catch (e) {
            // Cache fetch failed, fall through to live backend solver
        }

        // 2. Second attempt: Query Python FastAPI backend to compute or generate payload on demand
        try {
            console.log(`Querying backend solver for ${id} (${mode})...`);
            const backendResponse = await fetch(`${this.baseUrl}/scenario/${id}?solver=${encodeURIComponent(mode)}`);
            if (!backendResponse.ok) {
                throw new Error(`Backend solver HTTP error: ${backendResponse.status}`);
            }
            return await backendResponse.json();
        } catch (err) {
            console.error(`Failed to fetch scenario ${id} (${mode}) from backend:`, err);
            return { error: 'Network failure' };
        }
    }

    async fetchKKTQuery(pointVec, timeInt) {
        try {
            const res = await fetch(`${this.baseUrl}/kkt_query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    point: [pointVec.x, pointVec.y, pointVec.z],
                    t: timeInt || 0
                })
            });
            if (res.ok) {
                return await res.json();
            }
        } catch (e) {
            // Backend offline fallback
        }
        return { hyperplanes: [] };
    }
}